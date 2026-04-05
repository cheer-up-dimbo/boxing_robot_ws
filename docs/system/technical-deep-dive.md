# BoxBunny Technical Deep Dive

This document covers the engineering decisions, design rationale, and integration challenges behind the BoxBunny system. It complements the architecture docs with the "why" behind the "what".

---

## 1. Hardware Platform

### Jetson Orin NX 8GB

| Spec | Value |
|------|-------|
| GPU | NVIDIA Ampere (1024 CUDA cores, 32 Tensor Cores) |
| CPU | 6-core Arm Cortex-A78AE |
| RAM | 8GB LPDDR5 (shared CPU/GPU) |
| Storage | NVMe SSD |
| AI Performance | Up to 100 TOPS (INT8) |
| Power | 10-25W configurable |
| OS | JetPack 5.x (Ubuntu 20.04 / L4T) |

The Jetson was chosen because it runs the full AI pipeline locally (CV inference + LLM) without internet. The 8GB shared memory is the primary constraint — CV and LLM must share the GPU carefully.

### Intel RealSense D435i

| Spec | Value |
|------|-------|
| RGB Resolution | 1920x1080 @ 30fps (used at 960x540) |
| Depth Resolution | 1280x720 @ 30fps (used at 640x480) |
| Depth Range | 0.3m - 3.0m (usable for boxing) |
| IMU | Built-in accelerometer + gyroscope |
| Interface | USB 3.0 |
| Field of View | 87° x 58° (depth) |

Downscaled to 960x540 RGB and 640x480 depth to reduce GPU memory usage while maintaining sufficient resolution for pose estimation.

### Teensy 4.1 Microcontroller

| Spec | Value |
|------|-------|
| Processor | ARM Cortex-M7, 600MHz |
| IMU Sensors | 4 pad accelerometers + 2 arm accelerometers |
| Communication | USB Serial (115200 baud) via micro-ROS |
| Sampling Rate | 100Hz per sensor |
| Pad Mapping | 0=centre, 1=right, 2=left, 3=head |

The IMU pads detect punch impacts via accelerometer spikes. Gravity is auto-calibrated from the first 500 samples (~2.5 seconds at startup). Impact threshold: 5.0 m/s² after gravity subtraction.

### Robot Arm

| Spec | Value |
|------|-------|
| DOF | 2 (yaw rotation + strike extension) |
| Motors | Dynamixel servos |
| Speed Presets | Slow (8 rad/s), Medium (15), Fast (25), Max (30) |
| Punch Codes | 1=jab, 2=cross, 3=L hook, 4=R hook, 5=L uppercut, 6=R uppercut |
| Control | micro-ROS via Teensy 4.1 |

---

## 2. Computer Vision Pipeline

### Why Direct Camera Access (No ROS Camera Driver)

The CV node (`cv_node.py`) opens the RealSense camera directly via `pyrealsense2` rather than using the standard ROS 2 RealSense driver. Reasons:

1. **Conda Environment Isolation** — The CV model requires PyTorch, TensorRT, and pyrealsense2 from a conda environment (`boxing_ai`). The ROS camera driver runs in the system Python. Having cv_node own the camera avoids cross-environment dependency conflicts.

2. **Frame Rate Control** — The action recognition model was trained at exactly 30fps. The model's temporal window (12 frames) assumes consistent 33ms frame intervals. If frames arrive at inconsistent rates, the voxel delta features (which measure motion between frames) become unreliable and accuracy drops significantly.

3. **GPU Memory Management** — Direct access allows the node to control exactly when frames are copied to GPU memory, avoiding unnecessary copies from a separate camera driver process.

### Frame Sharing Architecture

The CV node captures frames and publishes them to ROS topics for other consumers:

```
RealSense D435i (USB 3.0)
    |
    v
cv_node.py (direct pyrealsense2 access)
    |
    +---> /camera/color/image_raw ---------> gesture_node (MediaPipe hands)
    |                                   +--> reaction_test_page (YOLO pose)
    |
    +---> /camera/aligned_depth_to_color --> cv_node internal (voxel features)
    |
    +---> /boxbunny/cv/detection ----------> punch_processor (fusion)
    +---> /boxbunny/cv/user_tracking ------> session_manager (movement data)
    +---> /boxbunny/cv/person_direction ---> session_manager (direction tracking)
```

Multiple consumers subscribe to the same published image topics. The cv_node is the single camera owner — no other node opens the hardware directly.

### FPS Sensitivity and Model Accuracy

The FusionVoxelPoseTransformerModel is extremely sensitive to input frame rate:

- **Trained at 30fps** — The model's temporal features expect exactly 33ms between frames
- **Voxel delta features** use 2-frame and 8-frame differences:
  - Channel 0: Delta @2 frames (67ms) — captures fast motion onset (e.g., jab extension)
  - Channel 1: Delta @8 frames (267ms) — captures sustained motion (e.g., hook arc)
- **If FPS drops** (e.g., to 15fps), the 2-frame delta now spans 133ms instead of 67ms. A jab that takes ~200ms would appear as a slow movement, and the model misclassifies it
- **If FPS increases** (e.g., to 60fps), deltas become too small to detect meaningful motion

**Solution — Adaptive Frame Rate**:
- During active sessions: inference runs at full 30fps (every frame)
- During idle: drops to ~6fps to save GPU for LLM
- The `inference_interval` parameter controls this (set to 1 for every frame, higher values skip frames)

### TensorRT Optimization

Both the action model and YOLO pose model are converted to TensorRT FP16 engines on first run:

1. PyTorch model → ONNX export → TensorRT engine (cached to disk)
2. Subsequent launches load the cached engine directly (~2s vs ~30s first-time build)
3. FP16 inference: ~8ms per frame for action model, ~6ms for YOLO pose
4. Combined throughput: ~42fps (above the 30fps requirement)

### Post-Processing Pipeline

Raw model outputs go through multiple smoothing stages to reduce jitter:

```
Raw logits → Softmax → EMA smoothing (α=0.35) → Hysteresis (margin=0.12)
         → State machine (min hold 3 frames, sustain conf 0.78)
         → Final prediction
```

- **EMA smoothing**: Exponential moving average prevents single-frame spikes
- **Hysteresis**: Requires 12% confidence margin to switch classes (prevents oscillation between similar punches)
- **State machine**: Actions must persist for 3+ frames to be confirmed, and confidence must stay above 78% to sustain the action

---

## 3. Local LLM Integration

### Model Selection

| Property | Value |
|----------|-------|
| Model | Qwen2.5-3B-Instruct |
| Format | GGUF (Q4_K_M quantization) |
| File Size | ~2GB |
| Context Window | 2048 tokens |
| Max Output | 128 tokens |
| Temperature | 0.7 |
| Library | llama-cpp-python |

Qwen2.5-3B was chosen because:
- Small enough to fit in Jetson's 8GB shared memory alongside CV models
- Instruction-tuned for following coaching prompts
- GGUF Q4_K_M quantization reduces memory to ~2GB while maintaining quality
- Generates coherent 1-2 sentence tips in <2 seconds

### GPU Memory Sharing with CV

The Jetson has 8GB shared between CPU and GPU. The allocation strategy:

| Component | GPU Memory | When Active |
|-----------|-----------|-------------|
| TensorRT action model | ~200MB | Always loaded |
| TensorRT YOLO pose | ~150MB | Always loaded |
| LLM (Qwen 2.5-3B Q4) | ~2GB | Preloaded at startup |
| Frame buffers | ~100MB | During capture |
| **Total** | **~2.5GB** | **Simultaneous** |

The LLM uses `n_gpu_layers: -1` (all layers on GPU) for fastest inference. With Q4 quantization, the model fits comfortably alongside the CV models.

### How the LLM Pipeline Works

```
Session Active
    |
    v
Every 18 seconds: _tip_tick() checks if enough time has passed
    |
    v
Builds context from recent punches, combo progress, session stats
    |
    v
System prompt (embedded, 24 lines) + user context → LLM inference
    |
    v
Response cleaned (markdown stripped) → Published as CoachTip
    |
    v
GUI displays in CoachTipBar widget
```

### System Prompt Design

The LLM system prompt (embedded in `llm_node.py`) instructs the model to:

- Act as "BoxBunny AI Coach" with AIBA manual knowledge
- Know all 6 punch types and their codes
- Understand boxing styles (European, Russian, American, Cuban)
- Adjust advice to beginner/intermediate/advanced level
- Keep real-time tips to 1-2 sentences (prevents cut-off)
- Post-session analysis: 2-3 paragraphs with specific metrics
- Analyze movement data (depth, lateral, direction patterns)
- Output PLAIN TEXT only — no markdown formatting
- Optionally suggest drills in format: `[DRILL:Name|combo=1-2|rounds=2|work=60s|speed=Medium]`

### Preventing Cut-Off Responses

Several mechanisms ensure complete responses:

1. **Short max_tokens (128)** — Limits response length so the model finishes within budget
2. **System prompt instruction** — Explicitly says "keep tips SHORT (1-2 sentences)"
3. **Inference timeout (20s)** — Background thread with hard timeout prevents hangs
4. **Markdown stripping** — `_clean_markdown()` removes formatting artifacts: `**bold**`, `*italic*`, `# headers`, `- lists`
5. **Sentence completion** — The standalone chat GUI (`tools/llm_chat_gui.py`) detects if a response doesn't end with `.`, `!`, or `?` and generates 8-32 additional tokens to complete the thought

### Fallback System

When the LLM is unavailable (model file missing, GPU OOM, inference timeout):

- 65 pre-written tips in `config/fallback_tips.json`
- 4 categories: technique (15), encouragement (13), correction (13), suggestion (13)
- Random selection from appropriate category based on session context
- Consecutive failure tracking: after 3 failures, attempts model reload

### Boxing Knowledge Base (RAG Data)

The LLM has access to boxing knowledge sourced from open-source materials:

**Location:** `data/boxing_knowledge/` (17 documents across 8 categories)

| Category | Files | Source/Content |
|----------|-------|---------------|
| Techniques | 5 files | Jab, cross, hooks, uppercuts, stance & guard descriptions |
| Defense | 3 files | Blocking/parrying, slipping/head movement, footwork |
| Combinations | 3 files | Beginner (1-2, 1-1-2), intermediate (1-2-3-2), advanced (feints, pivots) |
| Training Plans | 2 files | 8-week beginner and intermediate programs |
| Conditioning | 1 file | Jump rope, shadow boxing, circuit training |
| Common Mistakes | 1 file | Top 10 beginner errors with corrections |
| Coaching | 1 file | Group class / circuit training guidance |
| FAQ | 1 file | General technique, equipment, safety Q&A |

**Additional references** in `data/knowledge/`:
- `boxing_knowledge.txt` — Comprehensive 100+ line knowledge base (orthodox stance, all punches, defensive techniques, AIBA training stages)
- `aiba_coaches_manual.pdf` — Official AIBA reference
- `aiba_apb_coaches_manual.pdf` — APB professional reference

This knowledge is injected into the LLM's context when generating coaching analysis, providing sport-specific terminology and training methodology.

### Phone Dashboard ↔ LLM Communication

The phone dashboard's chat feature communicates with the LLM through this path:

```
Phone (Vue SPA)
    |
    POST /api/chat/message  (HTTP over WiFi to Jetson)
    |
    v
FastAPI Backend (sessions.py / chat.py)
    |
    ROS 2 Service Call: /boxbunny/llm/generate
    |
    v
llm_node.py (runs on Jetson GPU)
    |
    llama-cpp-python → Qwen2.5-3B inference
    |
    v
Response returned via service → API response → Phone displays
```

The model runs entirely on the Jetson. The phone sends requests over the local WiFi network, and the Jetson returns the generated response. No internet connection is needed.

### LLM Testing

The notebook provides a dedicated LLM testing tool (`notebooks/scripts/test_llm.py`) that:

1. Checks that the model file exists at `models/llm/qwen2.5-3b-instruct-q4_k_m.gguf`
2. Fixes a common Jetson issue: conda's `libstdc++` conflicts with the system version
3. Launches `tools/llm_chat_gui.py` — a full PySide6 chat interface with:
   - Streaming token display (shows text appearing word-by-word)
   - Model selection from `config/llm_models.yaml`
   - Configurable system prompts
   - Conversation history
   - Sentence completion mode
   - Dark theme matching the main GUI

---

## 4. ROS Node Architecture and Performance

### Why 10 Separate Nodes

The system uses 10 ROS 2 nodes rather than a monolithic application for several reasons:

1. **Fault Isolation** — If the LLM node crashes (GPU OOM), the session manager and CV keep running
2. **Independent Restart** — Any node can be restarted without affecting others
3. **Resource Control** — Nodes can be assigned to different CPU cores or priority levels
4. **Development** — Teams can work on different nodes independently
5. **Testing** — Nodes can be tested in isolation with mock publishers

### Parallel Execution Performance

ROS 2 Humble uses DDS (Data Distribution Service) for inter-node communication:

- **Single-threaded executors** — Each node runs a single-threaded executor (simplifies state management)
- **Callback groups** — I/O-bound callbacks (IMU serial reads) don't block timer callbacks
- **Message queuing** — QoS depth of 10-50 messages prevents message loss during spikes
- **Minimal serialization** — Messages are small structs (< 1KB each), serialization overhead is negligible

**CPU Load Distribution**:

| Node | CPU Usage | Notes |
|------|-----------|-------|
| cv_node | 1 core (heavy) | GPU-bound, CPU for pre/post processing |
| imu_node | <5% | Serial I/O, simple processing |
| punch_processor | <5% | Ring buffer operations |
| session_manager | <5% | State machine, accumulation |
| sparring_engine | <5% | Markov chain lookups |
| drill_manager | <5% | Sequence matching |
| analytics_node | <5% | Periodic JSON publish |
| llm_node | 1 core (burst) | GPU-bound during inference, idle otherwise |
| robot_node | <5% | Motor command forwarding |
| gesture_node | <10% | MediaPipe inference (optional) |

The Jetson's 6 CPU cores handle this comfortably. The bottleneck is GPU memory (shared between CV and LLM), not CPU.

### Topic Configuration

All ROS topic names are defined in `config/ros_topics.yaml` and loaded at startup by `constants.py`. This means:

- Topic names can be changed in one file without editing Python code
- The `Topics` and `Services` classes provide autocompletion in IDEs
- Typos in topic names are caught at import time rather than runtime

---

## 5. Vue Mobile Dashboard Build System

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Vue 3 | 3.4.21 |
| Build Tool | Vite | 5.1.4 |
| State Management | Pinia | 2.1.7 |
| Routing | Vue Router | 4.3.0 |
| Styling | Tailwind CSS | 3.4.1 |
| Charts | Chart.js + vue-chartjs | 4.4.1 / 5.3.0 |
| CSS Processing | PostCSS + Autoprefixer | 8.4.35 / 10.4.17 |
| Node.js | 18+ required | For Vite 5 |

### Build Process

```bash
cd src/boxbunny_dashboard/frontend

# Install dependencies (one-time)
npm install

# Development server (hot-reload)
npm run dev

# Production build (generates dist/)
npm run build

# Preview production build
npm run preview
```

The production build generates static files in `frontend/dist/` which the FastAPI backend serves as a Single Page Application (SPA). The backend has a catch-all route that returns `index.html` for any path not matching an API endpoint, enabling Vue Router's client-side routing.

### Design Approach

The dashboard was designed as a **mobile-first Progressive Web App (PWA)**:

- **Dark theme** matching the desktop GUI for visual consistency
- **Tailwind CSS utility classes** for rapid styling without custom CSS files
- **Responsive layout** optimized for phone screens (max-width containers)
- **Composition API** (Vue 3 `<script setup>`) for concise component logic
- **Pinia stores** for centralized state (auth tokens, session data, WebSocket connection)
- **Chart.js** for punch distribution and performance trend visualizations

---

## 6. Integration Challenges

### Teensy Simulator Duplicate Messages

**Problem:** During early development, the Teensy simulator was invaluable for testing without hardware. But when the V4 GUI (real motor control) was integrated alongside the simulator, both were publishing to the same ROS topics. This caused:

- Double-counted punches (IMU events from both simulator and real hardware)
- Conflicting robot commands (simulator sending strike feedback before real arm completed)
- Session state confusion (two sources of pad impacts with different timestamps)

**Root Cause:** The simulator had no awareness of whether real hardware was connected. It always published messages, even when real IMU data was flowing.

**Solution:** Added hardware detection to the simulator (`_teensy_connected` flag):

```python
# In teensy_simulator.py
def _on_real_strike(self, msg):
    """Detects real hardware is connected."""
    self._teensy_connected = True
    self._last_hw_time = time.time()

def publish_pad(self, pad, force):
    if self._teensy_connected:
        return  # Real hardware provides pad impacts
    # ... publish simulated impact
```

The simulator now subscribes to real hardware topics (`/robot/strike_detected`, `motor_feedback`). When it detects real messages, it sets `_teensy_connected = True` and stops publishing its own messages. If no real messages arrive for 3 seconds, it reverts to publishing simulated data. This allows running the simulator alongside real hardware for monitoring without interference.

### CV + IMU Timing Synchronization

**Problem:** CV predictions and IMU impacts arrive at different times. A jab might be detected by CV at frame N, but the IMU impact registers 50-200ms later (physical contact delay). Without synchronization, the system would either:
- Miss the match (if matching window too small)
- Match the wrong punch (if window too large)

**Solution:** Ring buffer-based fusion with a 500ms matching window:

1. CV detections go into a `PendingCV` ring buffer (max 50 entries, 2s expiry)
2. IMU impacts go into a `PendingIMU` ring buffer (max 50 entries, 2s expiry)
3. When a new event arrives, `pop_match()` searches the other buffer for the closest timestamp within 500ms
4. If matched: emit `ConfirmedPunch` with combined confidence
5. If unmatched after timeout: CV-only or IMU-only punch with penalty

### Camera Ownership Conflicts

**Problem:** Multiple components need camera access (main CV model, gesture recognition, reaction test). Standard approach of opening the camera in each component would fail (RealSense only allows one process).

**Solution:** Single-owner architecture. The `cv_node` exclusively owns the camera and publishes frames to ROS topics. All other consumers subscribe to these topics. This also ensures consistent frame rate for the action model (which is critical — see Section 2).

### GUI-Dashboard State Synchronization

**Problem:** The desktop GUI and phone dashboard both need to show the same training state, but they communicate through different channels (GUI uses ROS, dashboard uses HTTP/WebSocket).

**Solution:** Three synchronization mechanisms:
1. **Shared SQLite database** — Both read/write the same DB files. GUI writes session data via session_manager, dashboard reads via API queries
2. **JSON file polling** — Dashboard writes commands to `/tmp/boxbunny_gui_command.json`, GUI polls every 100ms
3. **WebSocket state buffering** — Dashboard backend buffers last known state per user, sends to phone on reconnect

---

## 7. Testing Strategy

### Bottom-Up Integration Approach

The notebook (`boxbunny_runner.ipynb`) was designed for bottom-up testing — each cell tests a progressively higher level of integration:

```
Level 1: Unit Tests (no hardware, no ROS)
    └── pytest: fusion logic, gamification math, database operations
    └── 146 tests, runs in ~8 seconds

Level 2: Integration Tests (no hardware, no ROS)
    └── Config loading, constant validation, message field checks
    └── Pad constraint verification, motor protocol, reaction detection
    └── 28 tests via test_integration.py

Level 3: Hardware Check (hardware required, no ROS)
    └── Verify each hardware component independently
    └── Camera, CUDA, models, database, audio

Level 4: Component Testing (individual subsystems)
    └── 3c: GUI Visual Test (GUI only, no ROS/hardware)
    └── 4a: CV Model Live Test (camera + CV, no ROS)
    └── 5b: LLM Coach Test (LLM only, no ROS)
    └── 5c: Sound Test (audio only)

Level 5: Subsystem Integration
    └── 3b: Simulator + Arms (Teensy + motors, no GUI)
    └── 4c: CV + IMU Fusion (camera + Teensy + fusion nodes)
    └── 4b: Reaction Test (GUI + camera + YOLO)

Level 6: Full System
    └── 2a: Dev Mode (all nodes + GUI + simulator)
    └── 2b: Production Mode (all nodes + GUI + real hardware)
    └── 3a: GUI + Simulator + Arms + ROS (full pipeline)
```

This approach means:
- **Level 1-2 catch logic bugs** before any hardware is needed
- **Level 3 catches hardware/driver issues** before trying to run the system
- **Level 4 tests each component in isolation** to identify which part fails
- **Level 5 tests pairs of components** to catch interface mismatches
- **Level 6 validates the full system** end-to-end

### What Each Test Level Catches

| Level | Example Bug Caught |
|-------|-------------------|
| Unit | Pad constraint logic wrong (jab accepted on left pad) |
| Integration | ROS message missing a field (accel_magnitude not in ConfirmedPunch) |
| Hardware | RealSense not connected, CUDA driver mismatch |
| Component | GUI page layout broken, LLM model file missing |
| Subsystem | Simulator sending duplicate messages alongside real hardware |
| Full | Session state machine transitions incorrect under real timing |

### Demo Data for Testing

The demo data seeder (`tools/demo_data_seeder.py`) creates 4 users with realistic training histories that match the actual data format produced by `session_manager._build_summary()`. This ensures:

- Dashboard displays real-looking data during demos
- Field names match between seeded data and live session data
- All dashboard views (history, trends, detail) have content to render
- Performance benchmarks can be tested against population norms
