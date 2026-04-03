#!/usr/bin/env python3
"""Fusion Monitor — shows raw CV detections, raw IMU events, and fusion results.

Subscribes to:
  /boxbunny/cv/detection      — every CV prediction (per-frame, including idle)
  /boxbunny/imu/punch_event   — raw IMU pad strikes (from imu_node)
  /boxbunny/punch/confirmed   — fused results from punch_processor

Shows a live scrolling log with color-coded entries and running stats.
"""
import threading
import time
import tkinter as tk
from collections import deque

try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    raise SystemExit("rclpy not found. Source ROS 2 first.")

try:
    from boxbunny_msgs.msg import ConfirmedPunch, PunchDetection, PunchEvent
except ImportError:
    raise SystemExit("boxbunny_msgs not found. Build workspace first.")

# Theme
BG = "#0B0F14"
SURFACE = "#131920"
SURFACE2 = "#1A2029"
FG = "#E6EDF3"
FG_DIM = "#8B949E"
FG_MUTED = "#484F58"
GREEN = "#56D364"
RED = "#FF5C5C"
AMBER = "#FFAB40"
BLUE = "#58A6FF"
PURPLE = "#BC8CFF"
PRIMARY = "#FF6B35"
FONT = "Helvetica"
FONT_M = "Monospace"


class FusionNode(Node):
    def __init__(self):
        super().__init__("fusion_monitor")
        self.cb_cv = None
        self.cb_imu = None
        self.cb_confirmed = None
        self.create_subscription(PunchDetection, "/boxbunny/cv/detection", self._on_cv, 50)
        self.create_subscription(PunchEvent, "/boxbunny/imu/punch_event", self._on_imu, 10)
        self.create_subscription(ConfirmedPunch, "/boxbunny/punch/confirmed", self._on_confirmed, 10)
        self.get_logger().info("Fusion monitor started")

    def _on_cv(self, msg):
        if self.cb_cv:
            self.cb_cv(msg.punch_type, msg.confidence, msg.consecutive_frames, msg.raw_class)

    def _on_imu(self, msg):
        if self.cb_imu:
            self.cb_imu(msg.pad, msg.level, msg.force_normalized, msg.accel_magnitude)

    def _on_confirmed(self, msg):
        if self.cb_confirmed:
            self.cb_confirmed(
                msg.punch_type, msg.pad, msg.cv_confidence,
                msg.imu_confirmed, msg.cv_confirmed, msg.accel_magnitude, msg.level,
            )


class FusionMonitor:
    def __init__(self, node):
        self._node = node

        # Stats
        self._cv_total = 0
        self._cv_actions = 0  # non-idle
        self._imu_total = 0
        self._confirmed_total = 0
        self._confirmed_both = 0  # CV + IMU
        self._confirmed_cv_only = 0
        self._confirmed_imu_only = 0
        self._last_action = ""
        self._last_action_time = 0.0

        self._root = tk.Tk()
        self._root.title("Fusion Monitor")
        self._root.configure(bg=BG)
        self._root.geometry("500x600")
        self._root.resizable(True, True)
        self._build()

        # Wire ROS callbacks → Tkinter thread
        node.cb_cv = lambda *a: self._root.after(0, lambda: self._on_cv(*a))
        node.cb_imu = lambda *a: self._root.after(0, lambda: self._on_imu(*a))
        node.cb_confirmed = lambda *a: self._root.after(0, lambda: self._on_confirmed(*a))

    def _build(self):
        r = self._root

        # Title
        top = tk.Frame(r, bg=SURFACE, height=40)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="Fusion Monitor", font=(FONT, 14, "bold"),
                 bg=SURFACE, fg=PRIMARY).pack(side="left", padx=12)
        self._lbl_last = tk.Label(top, text="--", font=(FONT, 12, "bold"),
                                  bg=SURFACE, fg=FG_DIM)
        self._lbl_last.pack(side="right", padx=12)

        # Stats row
        stats = tk.Frame(r, bg=SURFACE2)
        stats.pack(fill="x", padx=8, pady=(6, 0))

        for col, (label, color, key) in enumerate([
            ("CV Detections", BLUE, "cv"),
            ("IMU Strikes", AMBER, "imu"),
            ("Confirmed", GREEN, "ok"),
        ]):
            cell = tk.Frame(stats, bg=SURFACE2)
            cell.pack(side="left", expand=True, fill="x", padx=4, pady=6)
            tk.Label(cell, text=label, font=(FONT, 9),
                     bg=SURFACE2, fg=FG_MUTED).pack()
            lbl = tk.Label(cell, text="0", font=(FONT, 16, "bold"),
                           bg=SURFACE2, fg=color)
            lbl.pack()
            setattr(self, f"_stat_{key}", lbl)

        # Current detection (big)
        self._lbl_current = tk.Label(r, text="IDLE", font=(FONT, 24, "bold"),
                                     bg=BG, fg=FG_MUTED)
        self._lbl_current.pack(pady=(8, 0))
        self._lbl_current_info = tk.Label(r, text="conf: 0%  frames: 0",
                                          font=(FONT_M, 11), bg=BG, fg=FG_DIM)
        self._lbl_current_info.pack()

        # Log
        tk.Label(r, text="EVENT LOG", font=(FONT, 10, "bold"),
                 bg=BG, fg=FG_MUTED).pack(anchor="w", padx=12, pady=(8, 2))

        self._log = tk.Text(r, bg=SURFACE, fg=FG_DIM, font=(FONT_M, 10),
                            wrap="none", relief="flat", borderwidth=0,
                            highlightthickness=0, state="disabled")
        self._log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._log.tag_configure("cv_idle", foreground=FG_MUTED)
        self._log.tag_configure("cv_action", foreground=BLUE)
        self._log.tag_configure("imu", foreground=AMBER)
        self._log.tag_configure("confirmed", foreground=GREEN)
        self._log.tag_configure("cv_only", foreground=PURPLE)
        self._log.tag_configure("imu_only", foreground=AMBER)

    def _add_log(self, text, tag="cv_idle"):
        self._log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}] {text}\n", tag)
        lines = int(self._log.index("end-1c").split(".")[0])
        if lines > 200:
            self._log.delete("1.0", f"{lines - 150}.0")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _on_cv(self, ptype, conf, frames, raw):
        self._cv_total += 1

        # Update current detection display
        if ptype != "idle":
            self._cv_actions += 1
            color = BLUE
            self._lbl_current.configure(text=ptype.upper().replace("_", " "), fg=color)
            self._lbl_current_info.configure(
                text=f"conf: {conf:.0%}  frames: {frames}  raw: {raw}"
            )
            self._add_log(
                f"CV   {ptype:<16s} conf={conf:.0%}  frames={frames}",
                "cv_action",
            )
        else:
            self._lbl_current.configure(text="IDLE", fg=FG_MUTED)
            self._lbl_current_info.configure(text=f"conf: {conf:.0%}  frames: {frames}")
            # Don't log every idle frame — too noisy
            # Only log transition to idle
            if self._last_action and self._last_action != "idle":
                self._add_log(f"CV   idle", "cv_idle")

        self._last_action = ptype
        self._stat_cv.configure(text=str(self._cv_actions))

    def _on_imu(self, pad, level, force, accel):
        self._imu_total += 1
        self._stat_imu.configure(text=str(self._imu_total))
        self._add_log(
            f"IMU  pad={pad:<8s} level={level:<6s} accel={accel:.1f} m/s\u00B2",
            "imu",
        )

    def _on_confirmed(self, ptype, pad, cv_conf, imu, cv, accel, level):
        if ptype in ("idle", "unclassified"):
            return

        self._confirmed_total += 1

        if imu and cv:
            self._confirmed_both += 1
            tag = "confirmed"
            label = f"OK   {ptype:<16s} CV+IMU  pad={pad:<8s} accel={accel:.0f}"
        elif cv and not imu:
            self._confirmed_cv_only += 1
            tag = "cv_only"
            label = f"OK   {ptype:<16s} CV-only conf={cv_conf:.0%}"
        elif imu and not cv:
            self._confirmed_imu_only += 1
            tag = "imu_only"
            label = f"OK   {ptype:<16s} IMU-only pad={pad:<8s} accel={accel:.0f}"
        else:
            return

        self._stat_ok.configure(text=str(self._confirmed_total))
        self._add_log(label, tag)
        self._lbl_last.configure(text=ptype.upper().replace("_", " "), fg=GREEN)

    def run(self):
        self._root.mainloop()


def main():
    rclpy.init()
    node = FusionNode()
    t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    t.start()
    gui = FusionMonitor(node)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
