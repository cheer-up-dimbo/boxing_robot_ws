#!/bin/bash
# Download required models for BoxBunny
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$WS_ROOT/models"

echo "=== BoxBunny Model Download ==="

# --- LLM Model ---
LLM_DIR="$MODELS_DIR/llm"
LLM_FILE="$LLM_DIR/qwen2.5-3b-instruct-q4_k_m.gguf"
mkdir -p "$LLM_DIR"

if [ -f "$LLM_FILE" ]; then
    echo "[LLM] Already downloaded: $(basename $LLM_FILE)"
else
    echo "[LLM] Downloading Qwen2.5-3B-Instruct Q4_K_M..."
    echo "  This is a ~2GB download. Please wait..."

    # Try huggingface-cli first, fall back to wget
    if command -v huggingface-cli &>/dev/null; then
        huggingface-cli download Qwen/Qwen2.5-3B-Instruct-GGUF \
            qwen2.5-3b-instruct-q4_k_m.gguf \
            --local-dir "$LLM_DIR" \
            --local-dir-use-symlinks False
    else
        wget -q --show-progress \
            "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf" \
            -O "$LLM_FILE"
    fi

    if [ -f "$LLM_FILE" ]; then
        echo "[LLM] Download complete: $(du -h $LLM_FILE | cut -f1)"
    else
        echo "[LLM] ERROR: Download failed. Please download manually:"
        echo "  URL: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF"
        echo "  Save to: $LLM_FILE"
    fi
fi

# --- CV Model Check ---
CV_MODEL="$WS_ROOT/action_prediction/model/best_model.pth"
if [ -f "$CV_MODEL" ]; then
    echo "[CV]  Model present: $(du -h $CV_MODEL | cut -f1)"
else
    echo "[CV]  WARNING: Custom CV model not found at: $CV_MODEL"
    echo "       This is a custom trained model — cannot be auto-downloaded."
fi

# --- YOLO Pose Model Check ---
YOLO_MODEL="$WS_ROOT/action_prediction/model/yolo26n-pose.pt"
if [ -f "$YOLO_MODEL" ]; then
    echo "[YOLO] Model present: $(du -h $YOLO_MODEL | cut -f1)"
else
    echo "[YOLO] WARNING: YOLO pose model not found at: $YOLO_MODEL"
fi

echo ""
echo "=== Model Download Complete ==="
