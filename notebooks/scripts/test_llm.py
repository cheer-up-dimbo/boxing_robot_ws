"""Launch the LLM Chat GUI for interactive testing.

Opens the BoxBunny AI Coach chat window where you can type messages
and get responses from the local Qwen 2.5-3B model.
Close the window to end the test.
"""
import subprocess
import sys
import os
from pathlib import Path

WS = '/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws'
MODEL_PATH = os.path.join(WS, 'models/llm/qwen2.5-3b-instruct-q4_k_m.gguf')
GUI_PATH = os.path.join(WS, 'tools/llm_chat_gui.py')

if not os.path.exists(MODEL_PATH):
    print(f"Model not found at {MODEL_PATH}")
    print("Run: bash scripts/download_models.sh")
    raise SystemExit(1)

# Fix libstdc++ conflict on Jetson (conda vs system library mismatch)
conda_prefix = os.environ.get('CONDA_PREFIX', '')
if conda_prefix:
    conda_libstdcpp = os.path.join(conda_prefix, 'lib', 'libstdc++.so.6')
    if os.path.exists(conda_libstdcpp):
        os.environ['LD_PRELOAD'] = conda_libstdcpp

# Verify llama_cpp loads
try:
    from llama_cpp import Llama  # noqa: F401
    print("llama-cpp-python: OK")
except ImportError:
    print("Installing llama-cpp-python (one-time, may take a few minutes)...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install",
         "llama-cpp-python", "--quiet"],
    )
    print("llama-cpp-python: installed")

# Set up Qt platform
import PySide6
plugins = os.path.join(PySide6.__path__[0], 'Qt', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugins
if os.path.exists(os.path.join(plugins, 'libqxcb.so')):
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
else:
    os.environ['QT_QPA_PLATFORM'] = 'eglfs'

print(f"Model: {MODEL_PATH}")
print("Launching LLM Chat GUI...")
print("(Model loading takes 10-30 seconds)")
print("Close the window to end the test.\n")

subprocess.run([sys.executable, GUI_PATH], env=os.environ)

print("LLM Chat GUI closed.")
