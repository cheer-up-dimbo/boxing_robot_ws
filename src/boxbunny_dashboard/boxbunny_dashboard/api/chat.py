"""AI Coach chat endpoints for BoxBunny Dashboard.

Proxies messages to the ROS GenerateLlm service (or a direct LLM call)
and returns AI coaching responses. Stores chat history per user.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from boxbunny_dashboard.api.auth import get_current_user
from boxbunny_dashboard.db.manager import DatabaseManager

logger = logging.getLogger("boxbunny.dashboard.chat")
router = APIRouter()


# ---- Pydantic models ----

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: Dict[str, Any] = Field(default_factory=dict)
    image: Optional[str] = Field(None, description="Base64-encoded image (JPEG/PNG, max 5MB)")


class TrainingAction(BaseModel):
    """An actionable training suggestion embedded in a chat response."""
    label: str  # Button text
    type: str  # "training", "power_test", "reaction_test", "preset"
    config: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    timestamp: str
    actions: Optional[List[TrainingAction]] = None


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


def _get_user_history(db: DatabaseManager, user: dict) -> str:
    """Fetch recent training sessions for LLM context."""
    try:
        import sqlite3
        from pathlib import Path
        username = user.get("username", "")
        db_path = Path(db._data_dir) / "users" / username / "boxbunny.db"
        if not db_path.exists():
            return "No training history yet."
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT mode, difficulty, started_at, rounds_completed, rounds_total, "
            "work_time_sec, summary_json FROM training_sessions "
            "ORDER BY started_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if not rows:
            return "No training sessions recorded yet."
        lines = []
        for r in rows:
            summary = {}
            try:
                summary = json.loads(r["summary_json"] or "{}")
            except Exception:
                pass
            punches = summary.get("total_punches", 0)
            date = r["started_at"][:10] if r["started_at"] else "?"
            lines.append(
                f"- {date}: {r['mode']} ({r['difficulty']}), "
                f"{r['rounds_completed']}/{r['rounds_total']} rounds, "
                f"{punches} punches"
            )
        return "\n".join(lines)
    except Exception:
        return "Could not load training history."


def _build_system_prompt(user: dict, context: Dict[str, Any]) -> str:
    """Build a system prompt for the AI boxing coach."""
    level = user.get('level', 'beginner')
    name = user.get('display_name', 'Boxer')

    depth = context.pop("reply_depth", "normal")
    depth_instructions = {
        "short": (
            "- Keep replies very brief — 1-2 sentences max. Get straight to the point.\n"
        ),
        "normal": (
            "- Keep replies concise but complete — typically 2-4 sentences. "
            "Use more when the user asks for explanations or analysis.\n"
        ),
        "detailed": (
            "- Give thorough, in-depth replies. Explain the reasoning behind your advice. "
            "Use multiple paragraphs if needed to fully cover the topic. "
            "Include examples, drills context, and technique breakdowns.\n"
        ),
    }.get(depth, "- Keep replies concise but complete — typically 2-4 sentences.\n")

    return (
        f"You are BoxBunny AI Coach, a friendly and knowledgeable boxing trainer assistant "
        f"built into the BoxBunny training robot. The user's name is {name} (level: {level}). "
        "You are based on AIBA coaching methodology with deep knowledge of boxing techniques, "
        "training methods, stance, footwork, all punch types, defensive moves, combinations, "
        "physical conditioning, and fight strategy from European, Russian, American, and Cuban styles.\n\n"

        "CONVERSATION STYLE:\n"
        "- Be conversational and natural, like a real coach chatting with their boxer.\n"
        "- Match the tone of the user — if they ask a casual question, reply casually. "
        "If they ask something technical, go deeper.\n"
        + depth_instructions +
        "- Always finish your thoughts naturally. Never stop mid-sentence.\n"
        "- Use the user's name occasionally to keep it personal.\n"
        "- NEVER use markdown formatting like ** or * or # in your replies. Plain text only.\n\n"

        "TRAINING DRILL SYSTEM:\n"
        "The robot can load drills directly from your reply using special tags.\n"
        "When the user asks for a drill, training, or workout, you MUST end your reply with a drill tag.\n"
        "When the user is NOT asking for a drill, do NOT include any tags.\n\n"

        "Trigger phrases (user wants a drill): suggest a training, suggest a drill, "
        "give me a workout, what should I practice, what combo, set up a drill, I want to train\n\n"

        "Tag format:\n"
        "[DRILL:Name|combo=SEQUENCE|rounds=N|work=TIMEs|speed=Medium (2s)]\n"
        "[DRILL:Name|type=power_test]\n"
        "[DRILL:Name|type=reaction_test]\n\n"

        "Available combos: 1=jab, 2=cross, 3=L hook, 4=R hook, 5=L uppercut, 6=R uppercut. "
        "Combine them with dashes like 1-2, 1-2-3, 1-1-2, 1-2-5-2.\n\n"

        "EXAMPLE — user says 'suggest me a training':\n"
        "\"Great idea! A jab-cross drill is perfect for building your fundamentals and timing. "
        "Let's get you started. [DRILL:Jab-Cross Drill|combo=1-2|rounds=3|work=60s|speed=Medium (2s)]\"\n\n"

        "EXAMPLE — user says 'how do I improve my hooks?':\n"
        "\"Focus on rotating your hips and keeping your elbow at 90 degrees. "
        "The power comes from your core, not your arm.\"\n"
        "(No drill tag here because the user asked for advice, not a drill.)\n\n"

        "IMAGE QUERIES:\n"
        "- When the user sends an image, describe what you see and answer their question about it.\n"
        "- You can help identify food/drinks and estimate nutritional info, recognise sports equipment, "
        "analyse boxing stances or form from photos, or answer any visual question.\n"
        "- Keep image responses helpful and conversational.\n\n"

        f"USER'S RECENT TRAINING HISTORY:\n{context.get('history', 'No history available.')}"
    )


def _parse_actions(text: str) -> tuple:
    """Extract [DRILL:...] tags from LLM output and return (clean_text, actions)."""
    import re
    actions = []
    pattern = r'\[DRILL:([^]]+)\]'

    for match in re.finditer(pattern, text):
        tag = match.group(1)
        parts = tag.split('|')
        label = parts[0].strip()
        config = {}
        drill_type = "training"

        for part in parts[1:]:
            if '=' in part:
                k, v = part.split('=', 1)
                k, v = k.strip(), v.strip()
                if k == 'type':
                    drill_type = v
                elif k == 'combo':
                    config['combo_seq'] = v
                elif k == 'rounds':
                    config['Rounds'] = v
                elif k == 'work':
                    config['Work Time'] = v
                elif k == 'speed':
                    config['Speed'] = v

        route_map = {
            "training": "training_session",
            "power_test": "power_test",
            "reaction_test": "reaction_test",
            "stamina_test": "stamina_test",
        }
        config['route'] = route_map.get(drill_type, "training_session")
        config['name'] = label

        actions.append(TrainingAction(
            label=f"Start: {label}",
            type=drill_type,
            config=config,
        ))

    # Remove the tags from the text
    clean_text = re.sub(pattern, '', text).strip()
    # Clean up any double newlines left by tag removal
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

    return clean_text, actions if actions else None


# Singleton ROS node for dashboard LLM calls — avoids leaking nodes
_ros_node = None
_ros_client = None


def _get_ros_llm_client():
    """Get or create a persistent ROS node + LLM service client."""
    global _ros_node, _ros_client  # noqa: PLW0603
    try:
        import rclpy
        from boxbunny_msgs.srv import GenerateLlm

        if not rclpy.ok():
            rclpy.init()
        if _ros_node is None:
            _ros_node = rclpy.create_node("dashboard_llm_client")
            _ros_client = _ros_node.create_client(
                GenerateLlm, "/boxbunny/llm/generate",
            )
            logger.info("Dashboard LLM ROS client created")
        return _ros_node, _ros_client
    except Exception:
        return None, None


def _call_llm_sync(
    prompt: str, system_prompt: str, image_b64: Optional[str] = None,
) -> str:
    """Blocking LLM call via ROS service — run in a thread pool."""
    try:
        import rclpy
        from boxbunny_msgs.srv import GenerateLlm

        node, client = _get_ros_llm_client()
        if node is None or client is None:
            raise RuntimeError("ROS not available")

        if not client.wait_for_service(timeout_sec=5.0):
            logger.warning("LLM service not available within timeout")
            raise RuntimeError("LLM service not available")

        context = {"system_prompt": system_prompt}
        if image_b64:
            context["image_base64"] = image_b64

        req = GenerateLlm.Request()
        req.prompt = prompt
        req.context_json = json.dumps(context)
        req.system_prompt_key = "coach_chat"
        future = client.call_async(req)
        timeout = 45.0 if image_b64 else 25.0
        rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
        if future.result() is not None and future.result().success:
            return future.result().response
        logger.warning("LLM service returned failure or timed out")
    except Exception as exc:
        logger.warning("ROS LLM call failed: %s", exc, exc_info=True)

    return ""


async def _call_llm(
    prompt: str, system_prompt: str, image_b64: Optional[str] = None,
) -> str:
    """Call LLM via ROS service (llm_node on the Jetson). No local model."""
    loop = asyncio.get_event_loop()

    result = await loop.run_in_executor(
        None, _call_llm_sync, prompt, system_prompt, image_b64,
    )
    if result:
        _record_inference_success()
        return result

    _record_inference_failure()
    return (
        "Coach is temporarily unavailable. Try again in a moment. "
        "Quick tip: keep your guard up, rotate your hips on crosses, and breathe!"
    )


def _call_llm_direct_with_timeout(prompt: str, system_prompt: str) -> str:
    """Unused — kept for interface compatibility."""
    result = [None]
    def _infer():
        try:
            # Reset KV cache so each question starts fresh — no context buildup
            _direct_model.reset()
            resp = _direct_model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200, temperature=0.7,
            )
            result[0] = resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning("LLM direct inference error: %s", e)

    t = threading.Thread(target=_infer, daemon=True)
    t.start()
    t.join(timeout=15.0)
    if t.is_alive():
        logger.warning("LLM direct call timed out (15s)")
        return ""
    return result[0] or ""


# ---- Endpoints ----

# Track inference health for status endpoint
_last_inference_success: float = 0.0
_recent_inference_failures: int = 0


def _record_inference_success() -> None:
    """Record a successful inference for health tracking."""
    global _last_inference_success, _recent_inference_failures, _llm_verified  # noqa: PLW0603
    _last_inference_success = time.time()
    _recent_inference_failures = 0
    _llm_verified = True


def _record_inference_failure() -> None:
    """Record a failed inference for health tracking."""
    global _recent_inference_failures, _llm_verified  # noqa: PLW0603
    _recent_inference_failures += 1
    if _recent_inference_failures >= 2:
        _llm_verified = False


_llm_verified = False  # True only after a successful inference


@router.get("/status")
async def get_llm_status() -> dict:
    """Check if the LLM ROS service is actually reachable and working."""
    try:
        node, client = _get_ros_llm_client()
        if not (node and client and client.service_is_ready()):
            return {"ready": False, "source": "none", "message": "LLM service offline"}

        # If previously verified and no recent failures, skip the ping
        if _llm_verified and _recent_inference_failures < 2:
            return {"ready": True, "source": "ros"}

        # Do a real ping to verify the model is loaded and responding
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _call_llm_sync, "Say OK", "Reply with just OK",
        )
        if result:
            return {"ready": True, "source": "ros"}
        return {"ready": False, "source": "ros", "message": "LLM model loading..."}
    except Exception:
        return {"ready": False, "source": "none", "message": "LLM service offline"}


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> ChatResponse:
    """Send a message to the AI coach and get a response.

    Optionally accepts a base64-encoded image for vision queries (e.g.,
    identifying food/equipment). The image is passed to the LLM node which
    lazy-loads the vision projector on first use.
    """
    # Validate image if present
    image_b64 = None
    if body.image:
        max_image_bytes = 5 * 1024 * 1024  # 5MB
        if len(body.image) > max_image_bytes * 1.37:  # base64 overhead
            image_b64 = None
            logger.warning("Image too large, ignoring (max 5MB)")
        else:
            image_b64 = body.image

    # Fetch user's recent training history for context
    history_context = _get_user_history(db, user)
    context_with_history = {**body.context, "history": history_context}
    system_prompt = _build_system_prompt(user, context_with_history)
    reply = await _call_llm(body.message, system_prompt, image_b64=image_b64)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Persist both user message and reply in the user's session events
    username = user["username"]
    try:
        db.save_session_event(
            username=username,
            session_id="chat",
            timestamp=time.time(),
            event_type="chat_message",
            data={"role": "user", "content": body.message},
        )
        db.save_session_event(
            username=username,
            session_id="chat",
            timestamp=time.time(),
            event_type="chat_message",
            data={"role": "assistant", "content": reply},
        )
    except Exception:
        logger.warning("Failed to persist chat message for %s", username)

    # Parse action cards from the LLM output
    clean_reply, actions = _parse_actions(reply)

    return ChatResponse(reply=clean_reply, timestamp=timestamp, actions=actions)


@router.get("/history", response_model=List[ChatMessage])
async def get_chat_history(
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[ChatMessage]:
    """Return recent chat history for the authenticated user."""
    username = user["username"]
    detail = db.get_session_detail(username, "chat")
    if detail is None:
        return []

    events = detail.get("events", [])
    chat_events = [
        e for e in events
        if e.get("event_type") == "chat_message"
    ]
    messages: List[ChatMessage] = []
    for e in chat_events[-limit:]:
        data = e.get("data_json", "{}")
        if isinstance(data, str):
            data = json.loads(data)
        messages.append(ChatMessage(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=str(e.get("timestamp", "")),
        ))
    return messages
