"""Launch just the Teensy simulator for development."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess


def generate_launch_description() -> LaunchDescription:
    ws_root = Path(__file__).resolve().parents[3]

    return LaunchDescription([
        ExecuteProcess(
            cmd=["python3", str(ws_root / "tools" / "teensy_simulator.py")],
            name="teensy_simulator",
            output="screen",
        ),
    ])
