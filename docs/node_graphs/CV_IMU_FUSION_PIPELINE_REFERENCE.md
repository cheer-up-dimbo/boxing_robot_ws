# CV + IMU Sensor Fusion Pipeline Reference

> Complete reference for recreating the fusion pipeline diagram — every stage, threshold, and data dimension.

---

## 1. Camera Setup (RealSense D435i)

| Parameter | Value |
|---|---|
| RGB Resolution | 960x540 (downscaled to 384px width for inference) |
| Depth Resolution | 848x480 (aligned to RGB) |
| FPS | 30 Hz |
| Depth Scale | 0.001 (raw mm → meters) |
| Pitch Offset | 5.0 degrees (configurable) |
| Auto-Pitch | Optional, based on head position, 15px deadband |

---

## 2. YOLO Pose Estimation

| Parameter | Value |
|---|---|
| Architecture | YOLOv11 Pose |
| Input Size | 320px (configurable `imgsz`) |
| Confidence Threshold | 0.15 (permissive) |
| Output | 17 COCO keypoints per person |
| Inference Time | ~6 ms (TensorRT FP16) |

**7 Keypoints Used:**
| Index | Joint |
|---|---|
| 0 | Nose |
| 5 | Left Shoulder |
| 6 | Right Shoulder |
| 7 | Left Elbow |
| 8 | Right Elbow |
| 9 | Left Wrist |
| 10 | Right Wrist |

**Multi-Person Selection:** Prioritizes by `area / (1 + distance_to_center)`

---

## 3. Voxel Occupancy Grid

| Parameter | Value |
|---|---|
| Grid Dimensions | 12x12x12 (default, configurable to 20^3) |
| Centering | Person's center of mass |
| Spatial Extent X | ±0.8 m (left/right) |
| Spatial Extent Y | ±1.0 m (up/down) |
| Spatial Extent Z | ±0.6 m (forward/back) |
| Background Model | 90th percentile of first 30 frames |
| Foreground Threshold | bg_threshold_m = 0.15 m |
| Depth Weighting | Inverse depth (closer = stronger) |

**Multi-Scale Delta Channels (2 channels):**
| Channel | Lookback | Temporal Coverage |
|---|---|---|
| Scale 1 | 4 frames | ~133 ms @30fps |
| Scale 2 | 16 frames | ~533 ms @30fps |

**Flattened Output:** 12^3 = 1,728 floats per channel x 2 channels = **3,456 dims**

---

## 4. Pose Features (42 Dimensions)

**Static Features (26 dims):**
| Feature | Dims | Description |
|---|---|---|
| Normalized Joint Coords | 14 | 7 joints x (x, y) normalized by shoulder width |
| Joint Confidence Scores | 7 | Per-joint confidence from YOLO |
| Arm Extension Ratios | 2 | Wrist-to-shoulder distance / shoulder_width (L, R) |
| Shoulder Rotation | 1 | (R_shoulder_x - L_shoulder_x) / shoulder_width |
| Elbow Angles | 2 | Angle at elbow (0=bent, pi=straight), normalized [0,1] |

**Velocity Features (16 dims):**
| Feature | Dims | Description |
|---|---|---|
| Joint Velocities | 14 | Delta x,y per joint from previous frame |
| Arm Extension Rate | 2 | Delta(left_ext), Delta(right_ext) |

**Gating:** Pose embedding scaled by mean confidence of visible joints (suppresses noisy detections)

---

## 5. Temporal Window

| Parameter | Value |
|---|---|
| Window Size | 12 frames |
| Time Span | 400 ms @30fps |
| Stacking | Rolling deque of [voxel(3456) + pose(42)] per frame |
| Total Input | 12 x 3,498 = **41,976 floats** |

---

## 6. FusionVoxelPose Transformer Model

**Voxel Branch (Conv3D Stem):**
| Layer | Details |
|---|---|
| Input | (B*T, 2, 12, 12, 12) — dual-scale occupancy |
| Conv3D x3 | stride=2, BatchNorm, GELU; spatial 12→6→3→2 |
| Flatten | 64 channels x 8 spatial = 512 |
| Linear | 512 → d_model=192 |

**Pose Branch (MLP Encoder):**
| Layer | Details |
|---|---|
| Input | (B*T, 42) raw pose features |
| MLP | 2-layer with LayerNorm, GELU, dropout |
| Confidence Gating | Multiply by mean(conf[14:21]) |
| Output | 64 dims |

**Fusion Projection:**
| Step | Details |
|---|---|
| Concatenate | 192 (voxel) + 64 (pose) = 256 |
| Linear + LayerNorm | 256 → 192 |

**Temporal Transformer Encoder:**
| Parameter | Value |
|---|---|
| d_model | 192 |
| num_heads | 8 |
| num_layers | 4 |
| dim_feedforward | 576 (3x d_model) |
| Masking | Causal (autoregressive) |
| Dropout | 0.2 |
| Positional Encoding | Sinusoidal, max_len=200 |
| norm_first | True |

**Classifier Head:**
| Step | Details |
|---|---|
| Pooling | Mean + Max over sequence → (B, 384) |
| LayerNorm | 384 |
| Linear + GELU + Dropout | 384 → 96 |
| Linear | 96 → 8 classes |

**8 Output Classes:** jab, cross, left_hook, right_hook, left_uppercut, right_uppercut, block, idle

**Inference Time:** ~8 ms (TensorRT FP16)

---

## 7. Post-Processing & State Machine

**EMA Smoothing:**
| Parameter | Value |
|---|---|
| Alpha | 0.35 |
| Formula | smooth = alpha * new + (1-alpha) * prev |

**Hysteresis:**
| Parameter | Value |
|---|---|
| Margin | 0.12 |
| Effect | Prevents rapid class switching |

**Causal Action State Machine:**
| Parameter | Value |
|---|---|
| Enter Consecutive | 2 frames to activate |
| Exit Consecutive | 3 frames to deactivate |
| Min Hold Steps | 3 frames minimum |
| Sustain Confidence | 0.78 minimum to hold |
| Peak Drop Threshold | 0.02 max drop from peak |
| Block Consecutive | 4 frames to confirm block |

**Gating Logic:**
- Min confidence: 0.4
- Non-idle must exceed idle confidence
- Top class margin must be positive vs second class

**Output:** PunchDetection message at ~30 Hz

---

## 8. IMU Pipeline

**Raw Processing:**
| Parameter | Value |
|---|---|
| Gravity Calibration | Mean of first 500 samples (~2.5s) |
| Strike Threshold | 5.0 m/s^2 (after gravity subtraction) |

**Force Classification:**
| Level | Accel Range | Normalized Value |
|---|---|---|
| Light | 0-20 m/s^2 | 0.33 |
| Medium | 20-40 m/s^2 | 0.66 |
| Hard | 40+ m/s^2 | 1.0 |

**Pad Mapping (Teensy Index → Location):**
| Index | Pad Name |
|---|---|
| 0 | centre (body) |
| 1 | right (user's right) |
| 2 | left (user's left) |
| 3 | head |

**Debounce (Training Mode):**
| Parameter | Value |
|---|---|
| Per-Pad Cooldown | 350 ms |

**Debounce (Navigation Mode):**
| Parameter | Value |
|---|---|
| Per-Pad Cooldown | 300 ms |
| Global Cooldown | 200 ms |

**Mode Transition Grace Period:** 200 ms

---

## 9. Fusion Engine (punch_processor)

**CV Buffer:**
| Parameter | Value |
|---|---|
| Storage | List of (timestamp, punch_type, confidence) |
| Max Age | 0.8 seconds |
| Pruning | Remove entries older than 0.8s on each new event |

**Matching Algorithm (when IMU fires):**
1. Get pad location from IMU event
2. Query CV buffer for predictions valid on that pad (pad constraint filter)
3. Count frames per valid punch type (frame-count voting)
4. Select dominant type (most frames, not highest confidence)
5. Use max confidence for that dominant type
6. Remove matched predictions from buffer (prevent double-matching)

**Pad Constraint Filter:**
| Pad | Valid Punch Types |
|---|---|
| centre | jab, cross |
| left | left_hook, left_uppercut |
| right | right_hook, right_uppercut |
| head | jab, cross, left_hook, right_hook, left_uppercut, right_uppercut |

**Reclassification (on constraint violation):**
- Search secondary classes from transformer top-K
- Accept first secondary with confidence >= 0.25
- Otherwise → "unclassified"

**CV-Only Fallback:**
| Parameter | Value |
|---|---|
| Min Consecutive Frames | 3 |
| Min Confidence | 0.6 |
| Behavior | Emit ConfirmedPunch without IMU |

**IMU-Only Fallback (no CV in buffer):**
| Parameter | Value |
|---|---|
| Default Confidence | 0.3 |
| Type Inference | centre→jab, left→left_hook, right→right_hook, head→jab |

---

## 10. Defense Detection

**Defense Window:**
| Parameter | Value |
|---|---|
| Trigger | RobotCommand message received |
| Duration | 500 ms |
| Accumulates | Arm strikes, CV blocks, user tracking |

**Classification Decision Tree (in order):**
| Priority | Condition | Result |
|---|---|---|
| 1 | Arm IMU contact = true | HIT |
| 2 | CV block confidence >= 0.3 | BLOCK |
| 3 | Lateral >= 40px OR depth >= 0.15m | SLIP |
| 4 | Lateral >= 20px OR depth >= 0.08m | DODGE |
| 5 | None of above | UNKNOWN |

**DefenseEvent Fields:**
```
float64 timestamp          # Robot punch start time
string arm                 # Robot's throwing arm
string robot_punch_code    # "1"-"6" punch code
bool struck                # true = contact, false = defended
string defense_type        # "block", "slip", "dodge", "hit", "unknown"
```

---

## 11. Downstream Consumers

**ConfirmedPunch → received by:**
| Node | Purpose |
|---|---|
| session_manager | Accumulate stats, save to DB |
| analytics_node | Real-time statistics |
| drill_manager | Combo sequence validation |
| sparring_engine | Counter-punch decisions |
| llm_node | Context for coaching tips |
| GUI (via bridge) | Live punch display |

**DefenseEvent → received by:**
| Node | Purpose |
|---|---|
| session_manager | Defense stats, save to DB |
| analytics_node | Defense rate breakdown |
| GUI (via bridge) | Defense indicator animation |

---

## 12. Message Fields

### PunchDetection (cv_node output)
```
float64 timestamp
string punch_type          # "jab", "cross", "left_hook", "right_hook",
                           # "left_uppercut", "right_uppercut", "block", "idle"
float32 confidence         # 0.0-1.0 (after EMA smoothing)
string raw_class           # Raw model output (before gating)
int32 consecutive_frames   # Frames with same prediction
```

### PunchEvent (imu_node output)
```
float64 timestamp
string pad                 # "left", "centre", "right", "head"
string level               # "light", "medium", "hard"
float32 force_normalized   # 0.33, 0.66, 1.0
float32 accel_magnitude    # Raw m/s^2
```

### ConfirmedPunch (punch_processor output)
```
float64 timestamp
string punch_type          # Classified punch type
string pad                 # Which pad was hit
string level               # "light", "medium", "hard", or "" if CV-only
float32 force_normalized   # 0.33/0.66/1.0 or 0.0 if CV-only
float32 cv_confidence      # From CV model (0.3 for IMU-only)
bool imu_confirmed         # true if pad impact matched
bool cv_confirmed          # true if CV prediction matched
float32 accel_magnitude    # Raw m/s^2
```

### UserTracking (cv_node auxiliary output)
```
float64 timestamp
float32 bbox_centre_x, bbox_centre_y
float32 bbox_top_y
float32 bbox_width, bbox_height
float32 depth              # Meters at bbox center
float32 lateral_displacement  # Pixels from baseline (neg=left, pos=right)
float32 depth_displacement    # Meters from baseline (neg=closer, pos=farther)
bool user_detected
```

### ArmStrikeEvent (imu_node output)
```
float64 timestamp
string arm                 # "left", "right"
bool contact               # true if struck user
```

---

## 13. Complete Data Flow (for diagram)

```
SENSOR LAYER
  RealSense D435i ──USB 3.0──→ [RGB 960x540] + [Depth 848x480 aligned] @30fps
  Teensy 4.1 ──micro-ROS──→ [PadImpact x4] @100Hz + [ArmStrike x2]

CV BRANCH (runs in cv_node)
  RGB Frame ──→ YOLO Pose (320px, TensorRT, ~6ms) ──→ 7 Keypoints + Confidences
  Depth Frame ──→ Voxel Grid (12^3, person-centric) ──→ Multi-Scale Delta (2ch, 3456 dims)
  Keypoints ──→ Pose Features (42 dims: coords + velocities + angles)
  [Voxel 3456 + Pose 42] ──→ Temporal Window (12 frames, 400ms)
  Window ──→ FusionVoxelPose Transformer (TensorRT, ~8ms)
  Logits ──→ EMA (a=0.35) → Hysteresis (0.12) → State Machine (2in/3out/3hold)
  Output: PunchDetection {type, confidence, consecutive_frames} @30Hz

IMU BRANCH (runs in imu_node)
  Raw Accel ──→ Gravity Calibration ──→ Threshold (5.0 m/s^2)
  ──→ Per-Pad Debounce (350ms) ──→ Force Classification (light/medium/hard)
  ──→ Pad Mapping (0=centre, 1=right, 2=left, 3=head)
  Output: PunchEvent {pad, level, force, accel} on-impact

FUSION (runs in punch_processor)
  CV buffer (0.8s) ←── PunchDetection
  IMU event ──→ Query buffer by pad constraints ──→ Frame-count voting
    ├── Match found → ConfirmedPunch (cv+imu)
    ├── No match → IMU-only fallback (conf=0.3, infer type from pad)
    └── CV-only path: 3+ frames >=0.6 conf → ConfirmedPunch (cv-only)
  Pad Constraint Violation → Reclassify (secondary >=0.25) or "unclassified"

DEFENSE (runs in punch_processor)
  RobotCommand received → Open 500ms window
  Accumulate: arm_event (contact), cv block, user_tracking (displacement)
  Close window → Classify: HIT > BLOCK > SLIP > DODGE > UNKNOWN
  Output: DefenseEvent {arm, punch_code, struck, defense_type}

DOWNSTREAM
  ConfirmedPunch → session_manager, analytics, drill_manager, sparring, llm, GUI
  DefenseEvent → session_manager, analytics, GUI
```

---

## 14. Configuration Reference (boxbunny.yaml)

```yaml
cv:
  checkpoint_path: ""
  yolo_model_path: ""
  device: "cuda:0"
  inference_interval: 1
  window_size: 12
  min_confidence: 0.4
  ema_alpha: 0.35
  hysteresis_margin: 0.12
  min_hold_frames: 3
  block_consecutive_needed: 4
  state_enter_consecutive: 2
  state_exit_consecutive: 2
  state_min_hold_steps: 2
  state_sustain_confidence: 0.78
  state_peak_drop_threshold: 0.02

fusion:
  fusion_window_ms: 500
  cv_unconfirmed_confidence_penalty: 0.3
  reclassify_min_secondary_confidence: 0.25
  imu_debounce_ms: 150
  defense_window_ms: 500
  slip_lateral_threshold_px: 40.0
  slip_depth_threshold_m: 0.15
  dodge_lateral_threshold_px: 20.0
  dodge_depth_threshold_m: 0.08
  block_cv_confidence_min: 0.3
  cv_only_min_consecutive_frames: 3
  cv_only_min_confidence: 0.7
  imu_only_default_confidence: 0.3
  imu_impact_threshold: 5.0
  imu_pad_map:
    0: "centre"
    1: "right"
    2: "left"
    3: "head"

imu:
  nav_debounce_ms: 300
  nav_global_debounce_ms: 200
  mode_transition_ms: 200
  heartbeat_interval_s: 1.0
```

---

## 15. Constants

**Punch Types (8 classes):** jab, cross, left_hook, right_hook, left_uppercut, right_uppercut, block, idle

**Pad Locations (4 pads):** left, centre, right, head

**Impact Levels (3):** light (0.33), medium (0.66), hard (1.0)

**Defense Types (5):** block, slip, dodge, hit, unknown
