# Boxing Action Prediction — Standalone Deployment

Real-time boxing action recognition using Intel RealSense D435i (RGB-D) depth camera, combining 3D voxel motion features with 2D pose estimation through a transformer-based fusion model.

## What This Does

A person stands in front of a RealSense D435i camera and throws boxing punches. The system classifies each action in real-time at 30fps:

**8 classes:** `jab`, `cross`, `left_hook`, `right_hook`, `left_uppercut`, `right_uppercut`, `block`, `idle`

**Best validation accuracy:** 96.6% (cross-person generalization — trained on 3 people, validated on 1 unseen person)

## How It Works

### Input Pipeline (30fps)
1. **RealSense D435i** captures synchronized RGB (960x540) + depth (848x480) at 30fps
2. **YOLO Pose** (yolo26n-pose, TensorRT FP16) detects 7 upper-body keypoints from RGB every frame
3. **Depth voxelization** converts the depth image into a 12x12x12 person-centric 3D occupancy grid

### Feature Extraction (per frame)

**Voxel features (3,456 dims)** — 2 channels of 12x12x12 = 1,728 voxels each:
| Channel | Content | What it captures |
|---|---|---|
| 0 | delta@2 frames (67ms at 30fps) | Fast motion — punch onset, jab snap |
| 1 | delta@8 frames (267ms at 30fps) | Sustained motion — full punch arc, hooks |

The voxel grid is person-centric (follows the person), gravity-aligned (corrected for camera tilt), and depth-weighted (closer = stronger signal).

**Pose features (42 dims)** — from YOLO Pose detection on RGB:

| Dims | Content | Purpose |
|---|---|---|
| 14 | Joint coordinates (x,y for 7 joints) | Where each joint is |
| 7 | Joint confidence scores | How reliable the detection is |
| 2 | Arm extension ratios | How far each arm is extended |
| 1 | Shoulder rotation | Body orientation |
| 2 | Elbow angles (0=bent, 1=straight) | Hook vs jab discrimination |
| 14 | Joint velocities (dx,dy per joint) | Which hand is moving, in what direction |
| 2 | Arm extension rate | Extending vs retracting |

### Model Architecture: `FusionVoxelPoseTransformerModel`

```
Input: (batch, T=12 frames, 3498 dims per frame)
                    |
        +-----------+-----------+
        |                       |
   Voxel branch            Pose branch
   (3,456 dims)            (42 dims)
        |                       |
   Conv3D Stem             PoseEncoder MLP
   3x stride-2 convs       42 -> 64 -> 64
   16 -> 32 -> 64          + confidence gating
        |                       |
   192-dim embedding       64-dim embedding
        |                       |
        +----------- concat ---+
                    |
              256 -> Linear -> 192-dim
              + LayerNorm
                    |
           Positional Encoding
                    |
           Transformer Encoder
           4 layers, 8 heads
           d=192, FFN=576
                    |
           Mean + Max pooling -> 384-dim
                    |
           Classifier Head -> 8-class logits
```

### GPU Optimization

Both models run as TensorRT FP16 engines on Jetson:
- **Action model:** `best_model.trt` (~8ms inference)
- **YOLO Pose:** `yolo26n-pose.engine` (~16ms inference, dynamic input)
- Total: ~24ms per frame = **~42fps** theoretical max on Orin NX 16GB

TensorRT engines are auto-generated on first run from the `.pth`/`.onnx` files and cached.

---

## Files

```
action_prediction/
    run.py                          <- Main entry point
    README.md                       <- This file
    live_voxelflow_inference.py     <- Inference engine + GUI
    lib/
        fusion_model.py             <- FusionVoxelPoseTransformerModel
        voxel_model.py              <- Conv3DStem, PositionalEncoding
        voxel_features.py           <- Voxel extraction from depth
        pose.py                     <- YOLO pose estimation wrapper
        __init__.py
    model/
        best_model.pth              <- Trained model checkpoint (v5, 96.6% val acc)
        best_model.onnx             <- ONNX export (auto-generated)
        best_model.trt              <- TensorRT engine (auto-generated on Jetson)
        yolo26n-pose.pt             <- YOLO Pose weights (PyTorch)
        yolo26n-pose.engine         <- YOLO Pose TensorRT engine (dynamic input, FP16)
    __init__.py
```

## Setup

```bash
# Python 3.10+ required
# CRITICAL: numpy must be <2.0 for Jetson torch compatibility
pip install torch numpy>=1.26,<2.0 opencv-python>=4.10,<4.11 pyrealsense2 ultralytics>=8.4.0

# TensorRT is required for 30fps — install via JetPack or symlink from system:
# ln -s /usr/lib/python3.10/dist-packages/tensorrt* $CONDA_PREFIX/lib/python3.10/site-packages/
```

## Usage

```bash
cd action_prediction

# Zero-config — all defaults work out of the box:
python run.py

# With video feed:
python run.py --show-video

# Recommended production config (matches training pipeline):
python run.py \
    --checkpoint model/best_model.pth \
    --pose-weights model/yolo26n-pose.engine \
    --device cuda:0 \
    --inference-interval 1 \
    --yolo-interval 1 \
    --downscale-width 384 \
    --min-confidence 0.8 \
    --ema-alpha 0.65 \
    --hysteresis-margin 0.04 \
    --min-hold-frames 1 \
    --processing-mode strict \
    --depth-res 848x480 \
    --optimize-gpu \
    --no-video \
    --camera-pitch 5

# Fall back to PyTorch YOLO (if TensorRT engine not available):
python run.py --pose-weights model/yolo26n-pose.pt --yolo-interval 3
```

## Parameters

### Speed vs Accuracy
| Param | Default | Description |
|---|---|---|
| `--inference-interval` | 1 | Predict every Nth frame (1=every, 2=skip half) |
| `--yolo-interval` | 1 | YOLO pose every Nth frame (1=best accuracy, 3=if using .pt) |
| `--downscale-width` | 384 | Feature resolution (256=fast, 384=balanced) |
| `--num-workers` | 1 | Parallel feature workers |

### Responsiveness
| Param | Default | Description |
|---|---|---|
| `--ema-alpha` | 0.65 | New prediction weight (0.35=smooth, 0.65=responsive, 1.0=raw) |
| `--hysteresis-margin` | 0.04 | Margin to switch class (0.12=sticky, 0.04=responsive) |
| `--min-hold-frames` | 1 | Hold prediction for N frames (3=sticky, 1=responsive) |
| `--temporal-smooth-window` | 1 | Smooth over N frames (1=raw, 3-5=stable) |
| `--min-confidence` | 0.8 | Below this -> idle (0.0=disabled, 0.9=strict) |

### Camera
| Param | Default | Description |
|---|---|---|
| `--depth-res` | 848x480 | Depth stream resolution |
| `--rgb-res` | 960x540 | RGB stream resolution |
| `--processing-mode` | strict | strict=ordered frames, latest=low latency |
| `--camera-pitch` | 5.0 | Camera tilt in degrees (positive=tilted down) |

### GPU Optimization
| Param | Default | Description |
|---|---|---|
| `--optimize-gpu` | on | Auto ONNX+TensorRT (FP16), cached after first run |
| `--no-optimize-gpu` | | Disable, use raw PyTorch |
| `--no-video` | on | Disable video for max throughput |
| `--show-video` | | Enable video rendering |

## Version History

| Version | Date | Val Accuracy | Notes |
|---|---|---|---|
| v5 (current) | 2026-04-02 | **96.6%** | Fusion voxel+pose, minimal augmentation, focal loss gamma 2.0, TensorRT for both models |

## Hardware Tested

- **NVIDIA Jetson Orin NX** (16GB, JetPack 6.1, CUDA 12.6, TensorRT 10.3)
- Intel RealSense D435i (firmware 5.17.0.10)
- Inference at 30fps prediction rate with TensorRT (both action model + YOLO)

## Known Issues

- **IMU not working on Jetson:** The D435i IMU requires `hid_sensor_hub` kernel module which is not included in the Tegra kernel. Use `--camera-pitch` to set tilt manually.
- **YOLO TensorRT overlay offset:** When using `.engine` for YOLO, the skeleton overlay draws at wrong coordinates (top-left corner). This is a visualization-only issue — the pose features are extracted correctly.
- **numpy version:** Must use numpy <2.0. The Jetson torch wheel crashes with numpy 2.x.
