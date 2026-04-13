#!/usr/bin/env python3
"""Test: CV person tracking → BLE base rotation.

Opens a debug GUI showing all CV values. BLE motor control is OFF by
default — press the ENABLE MOTOR button to connect and start sending
commands to the Arduino.
"""
import logging
import queue
import threading
import time
import tkinter as tk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("base_tracking")

# ── BLE constants (match ble_control.ino) ────────────────────────────
DEVICE_NAME = "BoxBunny Base"
SERVICE_UUID = "00001820-0000-1000-8000-00805f9b34fb"
CMD_UUID = "00002a68-0000-1000-8000-00805f9b34fb"
FEEDBACK_UUID = "00002a69-0000-1000-8000-00805f9b34fb"

TRACK_RPM = 500
MAX_DEPTH_M = 1.5

# ── Theme ────────────────────────────────────────────────────────────
BG = "#0B0F14"
SURFACE = "#131920"
FG = "#E6EDF3"
FG_DIM = "#8B949E"
GREEN = "#56D364"
RED = "#FF5C5C"
AMBER = "#FFAB40"
BLUE = "#58A6FF"
FONT = "Helvetica"

# ── Shared state ─────────────────────────────────────────────────────
_direction = "centre"
_direction_time = 0.0
_user_depth = 0.0
_user_detected = False
_bbox_cx = 0.0
_bbox_width = 0.0
_running = True


def _ros_listener():
    """Background thread: subscribe to person direction + user tracking."""
    global _direction, _direction_time, _user_depth, _user_detected
    global _bbox_cx, _bbox_width
    try:
        import rclpy
        from std_msgs.msg import String
        from boxbunny_msgs.msg import UserTracking
        rclpy.init()
        node = rclpy.create_node("base_tracking_test")

        def _on_direction(msg):
            global _direction, _direction_time
            _direction = msg.data.strip().lower()
            _direction_time = time.time()

        def _on_tracking(msg):
            global _user_depth, _user_detected, _bbox_cx, _bbox_width
            _user_detected = msg.user_detected
            if msg.user_detected:
                _bbox_cx = msg.bbox_centre_x
                _bbox_width = msg.bbox_width
                if msg.depth > 0:
                    _user_depth = msg.depth
            else:
                _user_depth = 0.0

        node.create_subscription(
            String, "/boxbunny/cv/person_direction", _on_direction, 10)
        node.create_subscription(
            UserTracking, "/boxbunny/cv/user_tracking", _on_tracking, 10)
        log.info("ROS: subscribed to person_direction + user_tracking")

        while _running:
            rclpy.spin_once(node, timeout_sec=0.1)

        node.destroy_node()
        rclpy.shutdown()
    except Exception as exc:
        log.error("ROS error: %s", exc)


class BaseTrackingGUI:
    """Debug GUI showing CV values with optional BLE motor control."""

    def __init__(self):
        self._root = tk.Tk()
        self._root.title("Base Tracking Debug")
        self._root.configure(bg=BG)
        self._root.geometry("480x620")
        self._root.resizable(True, True)

        self._ble_enabled = False
        self._ble_connected = False
        self._ble_cmd_queue = queue.Queue()
        self._last_cmd = ""
        self._base_deg = 0.0
        self._cmd_count = 0

        self._build_gui()
        self._update_loop()

    def _build_gui(self):
        r = self._root

        tk.Label(r, text="BASE TRACKING DEBUG", font=(FONT, 16, "bold"),
                 bg=BG, fg=BLUE).pack(pady=(12, 2))
        tk.Label(r, text="CV values \u2192 BLE motor commands", font=(FONT, 10),
                 bg=BG, fg=FG_DIM).pack(pady=(0, 10))

        # ── CV Detection card ────────────────────────────────────────
        cv_frame = tk.Frame(r, bg=SURFACE, bd=1, relief="flat",
                            highlightbackground="#2A3340", highlightthickness=1)
        cv_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(cv_frame, text="CV DETECTION", font=(FONT, 9, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", padx=10, pady=(8, 4))

        self._dir_lbl = tk.Label(cv_frame, text="---", font=(FONT, 36, "bold"),
                                 bg=SURFACE, fg=FG_DIM)
        self._dir_lbl.pack(pady=(0, 4))

        grid = tk.Frame(cv_frame, bg=SURFACE)
        grid.pack(fill="x", padx=10, pady=(0, 10))

        self._val_labels = {}
        for i, (name, default) in enumerate([
            ("Person", "---"), ("Depth", "---"), ("BBox CX", "---"),
            ("In Range", "---"), ("Age", "---"),
        ]):
            cell = tk.Frame(grid, bg=SURFACE)
            cell.grid(row=i // 3, column=i % 3, padx=8, pady=4, sticky="w")
            tk.Label(cell, text=name, font=(FONT, 8),
                     bg=SURFACE, fg=FG_DIM).pack(anchor="w")
            lbl = tk.Label(cell, text=default, font=("Courier", 14, "bold"),
                           bg=SURFACE, fg=FG)
            lbl.pack(anchor="w")
            self._val_labels[name] = lbl

        # ── Command output card ──────────────────────────────────────
        cmd_frame = tk.Frame(r, bg=SURFACE, bd=1, relief="flat",
                             highlightbackground="#2A3340", highlightthickness=1)
        cmd_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(cmd_frame, text="COMMAND OUTPUT", font=(FONT, 9, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", padx=10, pady=(8, 4))

        self._cmd_lbl = tk.Label(cmd_frame, text="S (STOP)",
                                 font=(FONT, 28, "bold"), bg=SURFACE, fg=FG_DIM)
        self._cmd_lbl.pack(pady=(0, 4))

        cmd_grid = tk.Frame(cmd_frame, bg=SURFACE)
        cmd_grid.pack(fill="x", padx=10, pady=(0, 10))

        for col, (label, attr, color) in enumerate([
            ("RPM", "_rpm_lbl", AMBER),
            ("Sent", "_sent_lbl", FG),
            ("Base Pos", "_pos_lbl", BLUE),
        ]):
            tk.Label(cmd_grid, text=label, font=(FONT, 8),
                     bg=SURFACE, fg=FG_DIM).grid(row=0, column=col, padx=8)
            lbl = tk.Label(cmd_grid, text=str(TRACK_RPM) if label == "RPM" else "---",
                           font=("Courier", 14, "bold"), bg=SURFACE, fg=color)
            lbl.grid(row=1, column=col, padx=8)
            setattr(self, attr, lbl)

        # ── BLE control ──────────────────────────────────────────────
        ble_frame = tk.Frame(r, bg=SURFACE, bd=1, relief="flat",
                             highlightbackground="#2A3340", highlightthickness=1)
        ble_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(ble_frame, text="BLE MOTOR CONTROL", font=(FONT, 9, "bold"),
                 bg=SURFACE, fg=FG_DIM).pack(anchor="w", padx=10, pady=(8, 4))

        self._ble_status = tk.Label(ble_frame, text="MOTOR OFF \u2014 debug only",
                                    font=(FONT, 12, "bold"), bg=SURFACE, fg=FG_DIM)
        self._ble_status.pack(pady=4)

        btn_row = tk.Frame(ble_frame, bg=SURFACE)
        btn_row.pack(pady=(4, 10))

        self._enable_btn = tk.Button(
            btn_row, text="ENABLE MOTOR", font=(FONT, 12, "bold"),
            bg="#333", fg=GREEN, activebackground=GREEN, activeforeground="black",
            relief="flat", padx=20, pady=10, command=self._toggle_ble)
        self._enable_btn.pack(side="left", padx=4)

        self._stop_btn = tk.Button(
            btn_row, text="EMERGENCY STOP", font=(FONT, 12, "bold"),
            bg="#333", fg=RED, activebackground=RED, activeforeground="white",
            relief="flat", padx=20, pady=10, state="disabled",
            command=self._emergency_stop)
        self._stop_btn.pack(side="left", padx=4)

        # ── Log ──────────────────────────────────────────────────────
        self._log_text = tk.Text(r, height=6, bg="#111", fg=FG_DIM,
                                 font=("Courier", 9), state="disabled",
                                 wrap="word", bd=0)
        self._log_text.pack(fill="x", padx=16, pady=(4, 12))

        self._root.protocol("WM_DELETE_WINDOW", self._quit)

    def _log(self, msg: str):
        stamp = time.strftime("%H:%M:%S")
        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"[{stamp}] {msg}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _compute_command(self) -> str:
        """What command should be sent based on current CV state."""
        age = time.time() - _direction_time if _direction_time > 0 else 999
        person_close = _user_detected and 0 < _user_depth <= MAX_DEPTH_M

        if age > 2.0:
            return "S"
        if not person_close:
            return "S"
        if _direction == "left":
            return f"L:{TRACK_RPM}"
        if _direction == "right":
            return f"R:{TRACK_RPM}"
        return "S"

    def _update_loop(self):
        """10Hz GUI update + BLE command dispatch."""
        if not _running:
            self._root.destroy()
            return

        age = time.time() - _direction_time if _direction_time > 0 else 999

        # ── Update CV display ────────────────────────────────────────
        dir_upper = _direction.upper()
        dir_color = (GREEN if _direction == "centre" else
                     AMBER if _direction in ("left", "right") else FG_DIM)
        self._dir_lbl.configure(text=dir_upper, fg=dir_color)

        self._val_labels["Person"].configure(
            text="YES" if _user_detected else "NO",
            fg=GREEN if _user_detected else RED)

        depth_str = f"{_user_depth:.2f}m" if _user_depth > 0 else "---"
        self._val_labels["Depth"].configure(
            text=depth_str,
            fg=(GREEN if 0 < _user_depth <= MAX_DEPTH_M else
                RED if _user_depth > MAX_DEPTH_M else FG_DIM))

        self._val_labels["BBox CX"].configure(
            text=f"{_bbox_cx:.0f}" if _user_detected else "---",
            fg=FG if _user_detected else FG_DIM)

        in_range = _user_detected and 0 < _user_depth <= MAX_DEPTH_M
        self._val_labels["In Range"].configure(
            text="YES" if in_range else "NO",
            fg=GREEN if in_range else RED)

        self._val_labels["Age"].configure(
            text=f"{age:.1f}s" if _direction_time > 0 else "---",
            fg=GREEN if age < 2.0 else RED)

        # ── Update command display ───────────────────────────────────
        cmd = self._compute_command()
        if cmd == "S":
            self._cmd_lbl.configure(text="S (STOP)", fg=FG_DIM)
        elif cmd.startswith("L:"):
            self._cmd_lbl.configure(text=f"\u2190 LEFT {TRACK_RPM}", fg=GREEN)
        elif cmd.startswith("R:"):
            self._cmd_lbl.configure(text=f"RIGHT {TRACK_RPM} \u2192", fg=BLUE)

        self._sent_lbl.configure(text=str(self._cmd_count))
        self._pos_lbl.configure(
            text=f"{self._base_deg:.1f}\u00B0" if self._ble_connected else "---")

        # ── Send BLE command if motor enabled ────────────────────────
        if self._ble_enabled and self._ble_connected and cmd != self._last_cmd:
            self._ble_cmd_queue.put(cmd)
            self._last_cmd = cmd
            self._cmd_count += 1
            self._log(f"\u2192 {cmd}")

        self._root.after(100, self._update_loop)

    # ── BLE management ───────────────────────────────────────────────

    def _toggle_ble(self):
        if self._ble_enabled:
            self._disable_ble()
        else:
            self._enable_ble()

    def _enable_ble(self):
        self._ble_status.configure(text="Connecting...", fg=AMBER)
        self._enable_btn.configure(state="disabled")
        self._log("BLE: Scanning for Arduino...")
        threading.Thread(target=self._ble_thread, daemon=True).start()

    def _ble_thread(self):
        """Runs the entire BLE lifecycle in its own asyncio event loop."""
        import asyncio

        async def _run():
            from bleak import BleakClient, BleakScanner

            # Scan
            devices = await BleakScanner.discover(timeout=5.0)
            device = None
            for d in devices:
                if d.name and DEVICE_NAME in d.name:
                    device = d
                    break
            if not device:
                self._root.after(0, lambda: self._on_ble_failed("Arduino not found"))
                return

            # Connect
            async with BleakClient(device.address, timeout=10.0) as client:
                # Feedback notifications
                def _on_fb(_sender, data: bytearray):
                    try:
                        parts = data.decode("utf-8", errors="ignore").split(",")
                        if len(parts) >= 6:
                            self._base_deg = float(parts[0])
                    except ValueError:
                        pass

                try:
                    await client.start_notify(FEEDBACK_UUID, _on_fb)
                except Exception:
                    pass

                self._root.after(0, self._on_ble_connected)

                # Command loop — process queue from GUI thread
                while self._ble_enabled and _running:
                    try:
                        cmd = self._ble_cmd_queue.get_nowait()
                        await client.write_gatt_char(
                            CMD_UUID, cmd.encode("utf-8"))
                    except queue.Empty:
                        pass
                    except Exception as exc:
                        self._root.after(
                            0, lambda e=str(exc): self._log(f"BLE write error: {e}"))
                    await asyncio.sleep(0.05)

                # Stop motor before disconnect
                try:
                    await client.write_gatt_char(CMD_UUID, b"S")
                except Exception:
                    pass

        try:
            asyncio.run(_run())
        except Exception as exc:
            self._root.after(0, lambda: self._on_ble_failed(str(exc)))
        finally:
            # BLE thread ended — ensure GUI knows we're disconnected
            self._root.after(0, self._on_ble_disconnected)

    def _on_ble_disconnected(self):
        """Called when BLE thread exits for any reason."""
        if self._ble_connected:
            self._ble_connected = False
            self._ble_enabled = False
            self._last_cmd = ""
            self._ble_status.configure(text="BLE disconnected", fg=RED)
            self._enable_btn.configure(text="ENABLE MOTOR", bg="#333", fg=GREEN,
                                       state="normal")
            self._stop_btn.configure(state="disabled")
            self._log("BLE: Connection lost")

    def _on_ble_connected(self):
        self._ble_enabled = True
        self._ble_connected = True
        self._last_cmd = ""
        self._ble_status.configure(text="MOTOR ON \u2014 tracking active", fg=GREEN)
        self._enable_btn.configure(text="DISABLE MOTOR", bg="#333", fg=RED,
                                   state="normal")
        self._stop_btn.configure(state="normal")
        self._log("BLE: Connected \u2014 motor commands active")

    def _on_ble_failed(self, reason: str):
        self._ble_enabled = False
        self._ble_connected = False
        self._ble_status.configure(text=f"Failed: {reason}", fg=RED)
        self._enable_btn.configure(text="ENABLE MOTOR", bg="#333", fg=GREEN,
                                   state="normal")
        self._log(f"BLE: {reason}")

    def _disable_ble(self):
        # Queue a stop command before disabling
        if self._ble_connected:
            self._ble_cmd_queue.put("S")
            self._log("\u2192 S (motor off)")
        self._ble_enabled = False
        self._ble_connected = False
        self._last_cmd = ""
        self._ble_status.configure(text="MOTOR OFF \u2014 debug only", fg=FG_DIM)
        self._enable_btn.configure(text="ENABLE MOTOR", bg="#333", fg=GREEN)
        self._stop_btn.configure(state="disabled")

    def _emergency_stop(self):
        self._ble_cmd_queue.put("S")
        self._log("EMERGENCY STOP")
        self._disable_ble()

    def _quit(self):
        global _running
        if self._ble_connected:
            self._ble_cmd_queue.put("S")
            time.sleep(0.2)  # let BLE thread send the stop
        _running = False
        self._ble_enabled = False
        self._root.destroy()

    def run(self):
        ros_t = threading.Thread(target=_ros_listener, daemon=True)
        ros_t.start()
        time.sleep(0.5)
        self._log(f"Depth filter: {MAX_DEPTH_M}m  |  RPM: {TRACK_RPM}")
        self._log("Motor OFF \u2014 press ENABLE MOTOR to connect BLE")
        self._root.mainloop()


def main():
    gui = BaseTrackingGUI()
    gui.run()


if __name__ == "__main__":
    main()
else:
    main()
