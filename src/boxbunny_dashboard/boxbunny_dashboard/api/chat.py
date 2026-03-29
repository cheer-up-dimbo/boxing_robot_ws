"""AI Coach chat endpoints for BoxBunny Dashboard.

Proxies messages to the ROS GenerateLlm service (or a direct LLM call)
and returns AI coaching responses. Stores chat history per user.
"""

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


class ChatResponse(BaseModel):
    reply: str
    timestamp: str


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


def _build_system_prompt(user: dict, context: Dict[str, Any]) -> str:
    """Build a system prompt for the AI boxing coach."""
    return (
        "You are BoxBunny AI Coach, an expert boxing trainer assistant. "
        f"The user's name is {user.get('display_name', 'Boxer')} "
        f"(level: {user.get('level', 'beginner')}). "
        "Provide concise, actionable boxing advice. "
        "Reference their recent training data when available."
    )


async def _call_llm(prompt: str, system_prompt: str) -> str:
    """Attempt to call the LLM via ROS service, falling back to a stub.

    In production, this uses rclpy to call /boxbunny/llm/generate.
    """
    try:
        import rclpy
        from boxbunny_msgs.srv import GenerateLlm

        if not rclpy.ok():
            rclpy.init()
        node = rclpy.create_node("dashboard_llm_client")
        client = node.create_client(GenerateLlm, "/boxbunny/llm/generate")
        if client.wait_for_service(timeout_sec=2.0):
            req = GenerateLlm.Request()
            req.prompt = prompt
            req.system_prompt = system_prompt
            future = client.call_async(req)
            rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
            if future.result() is not None:
                node.destroy_node()
                return future.result().response
        node.destroy_node()
    except Exception:
        logger.debug("ROS LLM service unavailable, using fallback")

    return (
        "I'm currently running in offline mode. Connect the LLM service "
        "for personalized coaching feedback. In the meantime, remember: "
        "keep your guard up, rotate your hips on crosses, and breathe!"
    )


# ---- Endpoints ----

@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> ChatResponse:
    """Send a message to the AI coach and get a response."""
    system_prompt = _build_system_prompt(user, body.context)
    reply = await _call_llm(body.message, system_prompt)
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

    return ChatResponse(reply=reply, timestamp=timestamp)


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
