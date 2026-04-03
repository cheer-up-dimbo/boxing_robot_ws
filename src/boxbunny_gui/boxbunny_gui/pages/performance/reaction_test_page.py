"""Reaction time test page.

3 trials with countdown, random-delay green stimulus, and a "return to neutral"
phase between attempts. Uses YOLO pose estimation for motion detection with
live camera feed, plus IMU punch as backup trigger.

Flow per trial:
  1. "Get Ready" countdown (3-2-1)
  2. Red screen "WAIT..." (random 1.5-4s delay)
  3. Green screen "PUNCH NOW!" (pose detects motion > 20px)
  4. Shows result (e.g. "187 ms")
  5. "Return to neutral" (user must stand still for 1s before next trial)

After 3 trials: shows results with per-attempt breakdown, tier, and history.
"""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import cv2
import numpy as np

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QPushButton as _QPushButton

from boxbunny_gui.theme import Color, Icon, Size, font, badge_style, back_link_style, PRIMARY_BTN
from boxbunny_gui.widgets import BigButton, StatCard

if TYPE_CHECKING:
    from boxbunny_gui.gui_bridge import GuiBridge
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_TOTAL_TRIALS = 3
_MIN_DELAY_MS = 1500
_MAX_DELAY_MS = 4000
_MOTION_THRESHOLD = 20.0
_NEUTRAL_HOLD_S = 1.0  # seconds user must be still before next trial

_TIERS = [
    (150, "Lightning", Color.SUCCESS),
    (200, "Fast", Color.INFO),
    (280, "Average", Color.PRIMARY),
    (380, "Developing", Color.WARNING),
    (9999, "Slow", Color.DANGER),
]

_WS_ROOT = Path(__file__).resolve().parents[5]
_YOLO_POSE_PATH = _WS_ROOT / "action_prediction" / "model" / "yolo26n-pose.pt"


def _ms_color(ms: float) -> str:
    if ms < 180:
        return Color.SUCCESS
    if ms < 250:
        return Color.INFO
    if ms < 350:
        return Color.PRIMARY
    if ms < 450:
        return Color.WARNING
    return Color.DANGER


def _tier_for(avg: float) -> tuple:
    for threshold, name, color in _TIERS:
        if avg <= threshold:
            return name, color
    return "Slow", Color.DANGER


# ── States ───────────────────────────────────────────────────────────────────
_ST_IDLE = "idle"
_ST_COUNTDOWN = "countdown"
_ST_WAIT = "wait"          # red screen, random delay
_ST_STIMULUS = "stimulus"  # green screen, waiting for punch
_ST_RESULT = "result"      # showing this trial's time
_ST_NEUTRAL = "neutral"    # waiting for user to return to neutral
_ST_DONE = "done"          # all trials complete, showing results


class _ReactionCameraWorker(QObject):
    """Background worker for camera capture + YOLO pose estimation."""

    frame_ready = Signal(object)
    movement_detected = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._model = None
        self._prev_keypoints = None

    def reset_baseline(self) -> None:
        self._prev_keypoints = None

    def start_capture(self) -> None:
        self._running = True
        self._prev_keypoints = None
        try:
            from ultralytics import YOLO
            path = str(_YOLO_POSE_PATH) if _YOLO_POSE_PATH.exists() else "yolo11s-pose.pt"
            self._model = YOLO(path)
        except Exception as e:
            logger.warning("YOLO pose unavailable: %s", e)
            self._model = None

        try:
            import pyrealsense2 as rs
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            pipeline.start(config)
            self._run_rs(pipeline)
            pipeline.stop()
            return
        except Exception:
            pass

        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            try:
                self._run_cv(cap)
            finally:
                cap.release()

    def stop_capture(self) -> None:
        self._running = False

    def _run_rs(self, pipeline) -> None:
        while self._running:
            f = pipeline.wait_for_frames(timeout_ms=100)
            c = f.get_color_frame()
            if c:
                self._process(np.asanyarray(c.get_data()))

    def _run_cv(self, cap) -> None:
        while self._running:
            ok, bgr = cap.read()
            if ok:
                self._process(cv2.flip(bgr, 1))
            else:
                time.sleep(0.01)

    def _process(self, bgr: np.ndarray) -> None:
        display = bgr.copy()
        movement = 0.0
        if self._model is not None:
            try:
                results = self._model(bgr, verbose=False)
                kps = self._extract(results)
                if kps is not None:
                    self._draw(display, kps)
                    if self._prev_keypoints is not None:
                        movement = self._motion(self._prev_keypoints, kps)
                    self._prev_keypoints = kps
            except Exception:
                pass
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.frame_ready.emit(QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy())
        if movement > 0:
            self.movement_detected.emit(movement)

    @staticmethod
    def _extract(results):
        if not results or not results[0].keypoints or results[0].keypoints.data is None:
            return None
        a = results[0].keypoints.data.cpu().numpy()
        return a[0] if a.shape[0] > 0 else None

    @staticmethod
    def _motion(prev, curr, thr=0.3):
        d = 0.0
        for i in range(min(len(prev), len(curr))):
            if (len(prev[i]) >= 3 and prev[i][2] < thr) or (len(curr[i]) >= 3 and curr[i][2] < thr):
                continue
            d = max(d, float(np.sqrt((curr[i][0]-prev[i][0])**2 + (curr[i][1]-prev[i][1])**2)))
        return d

    @staticmethod
    def _draw(img, kps):
        for i in range(len(kps)):
            x, y = int(kps[i][0]), int(kps[i][1])
            if len(kps[i]) >= 3 and kps[i][2] > 0.3:
                cv2.circle(img, (x, y), 5, (0, 255, 0), -1)


class ReactionTestPage(QWidget):
    """3-trial reaction time test with countdown, neutral reset, and history."""

    def __init__(self, router: PageRouter, bridge: Optional[GuiBridge] = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._bridge = bridge
        self._state: str = _ST_IDLE
        self._trial: int = 0
        self._times: List[float] = []
        self._all_history: List[List[float]] = []
        self._stimulus_time: float = 0.0
        self._neutral_still_since: float = 0.0

        # Timers
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._on_delay_done)
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(100)
        self._tick_timer.timeout.connect(self._tick)

        self._countdown_val: int = 3
        self._cam_thread: Optional[QThread] = None
        self._cam_worker: Optional[_ReactionCameraWorker] = None
        self._last_movement: float = 0.0

        self._build_ui()
        if self._bridge:
            self._bridge.punch_confirmed.connect(self._on_punch)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 8, 24, 14)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(10)
        btn_back = _QPushButton(f"{Icon.BACK}  Back")
        btn_back.setStyleSheet(back_link_style())
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self._abort)
        top.addWidget(btn_back)
        title = QLabel("Reaction Time Test")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Color.TEXT};")
        top.addWidget(title)
        top.addStretch()
        self._trial_badge = QLabel(f"0 / {_TOTAL_TRIALS}")
        self._trial_badge.setStyleSheet(badge_style(Color.WARNING))
        top.addWidget(self._trial_badge)
        root.addLayout(top)
        root.addSpacing(6)

        # ── Camera + overlay ─────────────────────────────────────────────
        self._stim_widget = QWidget()
        self._stim_widget.setMinimumHeight(180)
        stim_stack = QStackedLayout(self._stim_widget)
        stim_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._video_label = QLabel()
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setStyleSheet(
            f"background-color: {Color.SURFACE}; border-radius: 12px;"
            f" border: 1px solid {Color.BORDER};"
        )
        stim_stack.addWidget(self._video_label)

        self._overlay = QLabel("Tap Start to begin")
        self._overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay.setWordWrap(True)
        self._overlay.setStyleSheet(
            f"background: transparent; color: {Color.TEXT_SECONDARY};"
            " font-size: 26px; font-weight: 700;"
        )
        stim_stack.addWidget(self._overlay)
        root.addWidget(self._stim_widget, stretch=1)
        root.addSpacing(6)

        # ── Trial cards ──────────────────────────────────────────────────
        trials_row = QHBoxLayout()
        trials_row.setSpacing(6)
        self._trial_cards: list[QWidget] = []
        for i in range(_TOTAL_TRIALS):
            card = QWidget()
            card.setFixedHeight(56)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(0, 6, 0, 6)
            cl.setSpacing(2)
            n = QLabel(f"Attempt {i+1}")
            n.setObjectName("num")
            n.setAlignment(Qt.AlignCenter)
            n.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {Color.TEXT_DISABLED}; background: transparent;")
            cl.addWidget(n)
            v = QLabel("--")
            v.setObjectName("val")
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Color.TEXT_DISABLED}; background: transparent;")
            cl.addWidget(v)
            card.setStyleSheet(f"background-color: {Color.SURFACE}; border-radius: {Size.RADIUS_SM}px;")
            trials_row.addWidget(card)
            self._trial_cards.append(card)
        root.addLayout(trials_row)
        root.addSpacing(8)

        # ── Start button ─────────────────────────────────────────────────
        self._btn_start = BigButton("Start Test", stylesheet=PRIMARY_BTN)
        self._btn_start.setFixedHeight(60)
        self._btn_start.clicked.connect(self._begin_test)
        root.addWidget(self._btn_start)

        # ── Results panel ────────────────────────────────────────────────
        self._results_w = QWidget()
        self._results_w.setObjectName("res")
        self._results_w.setStyleSheet(f"""
            QWidget#res {{ background-color: {Color.SURFACE}; border: 1px solid {Color.BORDER}; border-radius: {Size.RADIUS}px; }}
            QWidget#res QLabel {{ background: transparent; border: none; }}
        """)
        rl = QVBoxLayout(self._results_w)
        rl.setContentsMargins(16, 14, 16, 14)
        rl.setSpacing(10)

        # Hero: tier + average
        hero = QHBoxLayout()
        hero.setSpacing(14)
        self._tier_lbl = QLabel("--")
        self._tier_lbl.setAlignment(Qt.AlignCenter)
        self._tier_lbl.setFixedSize(120, 56)
        self._tier_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: #FFF; background-color: {Color.SURFACE_LIGHT}; border-radius: {Size.RADIUS}px;")
        hero.addWidget(self._tier_lbl)
        hero_v = QVBoxLayout()
        hero_v.setSpacing(0)
        self._avg_lbl = QLabel("-- ms")
        self._avg_lbl.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {Color.PRIMARY};")
        hero_v.addWidget(self._avg_lbl)
        hero_v.addWidget(QLabel("Average Reaction Time"))
        hero.addLayout(hero_v)
        hero.addStretch()
        rl.addLayout(hero)

        # Stats
        sr = QHBoxLayout()
        sr.setSpacing(8)
        self._s_best = StatCard("Best", "-- ms", accent=Color.SUCCESS)
        self._s_worst = StatCard("Worst", "-- ms", accent=Color.DANGER)
        self._s_spread = StatCard("Spread", "-- ms", accent=Color.INFO)
        sr.addWidget(self._s_best)
        sr.addWidget(self._s_worst)
        sr.addWidget(self._s_spread)
        rl.addLayout(sr)

        # Per-attempt breakdown
        rl.addWidget(QLabel(""))  # spacer
        self._breakdown_title = QLabel("ATTEMPT BREAKDOWN")
        self._breakdown_title.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {Color.TEXT_DISABLED}; letter-spacing: 1px;")
        rl.addWidget(self._breakdown_title)

        self._breakdown_row = QHBoxLayout()
        self._breakdown_row.setSpacing(6)
        self._breakdown_labels: list[QWidget] = []
        for i in range(_TOTAL_TRIALS):
            w = QWidget()
            w.setFixedHeight(50)
            wl = QVBoxLayout(w)
            wl.setContentsMargins(0, 4, 0, 4)
            wl.setSpacing(0)
            wl.addWidget(_centered_label(f"#{i+1}", 10, Color.TEXT_DISABLED))
            vl = _centered_label("--", 16, Color.TEXT_DISABLED)
            vl.setObjectName("bval")
            wl.addWidget(vl)
            w.setStyleSheet(f"background-color: {Color.BG}; border-radius: 6px;")
            self._breakdown_row.addWidget(w)
            self._breakdown_labels.append(w)
        rl.addLayout(self._breakdown_row)

        # History
        self._hist_title = QLabel("SESSION HISTORY")
        self._hist_title.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {Color.TEXT_DISABLED}; letter-spacing: 1px;")
        self._hist_title.setVisible(False)
        rl.addWidget(self._hist_title)

        self._hist_row = QHBoxLayout()
        self._hist_row.setSpacing(4)
        self._hist_labels: list[QLabel] = []
        for _ in range(5):
            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(26)
            lbl.setStyleSheet(f"font-size: 10px; color: {Color.TEXT_DISABLED}; background: {Color.BG}; border-radius: 4px;")
            self._hist_row.addWidget(lbl)
            self._hist_labels.append(lbl)
        rl.addLayout(self._hist_row)

        # Buttons
        br = QHBoxLayout()
        br.setSpacing(10)
        self._btn_retry = BigButton("Try Again", stylesheet=PRIMARY_BTN)
        self._btn_retry.setFixedHeight(50)
        self._btn_retry.clicked.connect(self._begin_test)
        br.addWidget(self._btn_retry)
        bd = _QPushButton("Done")
        bd.setFixedHeight(50)
        bd.setCursor(Qt.CursorShape.PointingHandCursor)
        bd.setStyleSheet(f"""
            QPushButton {{ background-color: {Color.SURFACE_LIGHT}; color: {Color.TEXT}; font-size: 15px; font-weight: 700; border: 1px solid {Color.BORDER_LIGHT}; border-radius: {Size.RADIUS}px; }}
            QPushButton:hover {{ background-color: {Color.SURFACE_HOVER}; }}
        """)
        bd.clicked.connect(lambda: self._router.navigate("performance"))
        br.addWidget(bd)
        rl.addLayout(br)

        self._results_w.setVisible(False)
        root.addWidget(self._results_w)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _set_bg(self, color: str) -> None:
        border = Color.BORDER if color == Color.SURFACE else color
        self._video_label.setStyleSheet(
            f"background-color: {color}; border-radius: 12px; border: 2px solid {border};"
        )

    def _set_overlay(self, text: str, size: int = 26, color: str = Color.TEXT_SECONDARY, bold: bool = True) -> None:
        weight = "800" if bold else "600"
        self._overlay.setText(text)
        self._overlay.setStyleSheet(
            f"background: transparent; color: {color}; font-size: {size}px; font-weight: {weight};"
        )

    def _reset_cards(self) -> None:
        for card in self._trial_cards:
            card.findChild(QLabel, "val").setText("--")
            card.findChild(QLabel, "val").setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Color.TEXT_DISABLED}; background: transparent;")
            card.setStyleSheet(f"background-color: {Color.SURFACE}; border-radius: {Size.RADIUS_SM}px;")

    # ── State machine ────────────────────────────────────────────────────

    def imu_start(self) -> None:
        if self._btn_start.isVisible():
            self._begin_test()

    def _begin_test(self) -> None:
        self._trial = 0
        self._times.clear()
        self._reset_cards()
        self._btn_start.setVisible(False)
        self._results_w.setVisible(False)
        # Camera already started on page enter
        self._tick_timer.start()
        self._start_countdown()

    def _start_countdown(self) -> None:
        self._state = _ST_COUNTDOWN
        self._countdown_val = 3
        self._set_bg(Color.SURFACE)
        self._set_overlay(str(self._countdown_val), size=48, color=Color.TEXT)
        self._delay_timer.start(1000)

    def _on_delay_done(self) -> None:
        if self._state == _ST_COUNTDOWN:
            self._countdown_val -= 1
            if self._countdown_val > 0:
                self._set_overlay(str(self._countdown_val), size=48, color=Color.TEXT)
                self._delay_timer.start(1000)
            else:
                # Countdown done → start first/next trial
                self._next_trial()
        elif self._state == _ST_WAIT:
            # Random delay done → show green stimulus
            self._show_stimulus()

    def _next_trial(self) -> None:
        self._trial += 1
        self._trial_badge.setText(f"{self._trial} / {_TOTAL_TRIALS}")
        self._state = _ST_WAIT
        self._set_bg(Color.DANGER)
        self._set_overlay("WAIT...", size=36, color="#FFFFFF")
        delay = random.randint(_MIN_DELAY_MS, _MAX_DELAY_MS)
        self._delay_timer.start(delay)

    def _show_stimulus(self) -> None:
        self._state = _ST_STIMULUS
        self._stimulus_time = time.monotonic()
        if self._cam_worker:
            self._cam_worker.reset_baseline()
        self._set_bg(Color.SUCCESS)
        self._set_overlay("PUNCH NOW!", size=40, color="#FFFFFF")

    def _tick(self) -> None:
        """100ms tick for neutral-hold detection."""
        if self._state != _ST_NEUTRAL:
            return
        # Check if user has been still long enough
        if self._last_movement < _MOTION_THRESHOLD * 0.5:
            if time.monotonic() - self._neutral_still_since >= _NEUTRAL_HOLD_S:
                # User is neutral → next trial or results
                if self._trial >= _TOTAL_TRIALS:
                    self._tick_timer.stop()
                    self._show_results()
                else:
                    self._start_countdown()
        else:
            self._neutral_still_since = time.monotonic()

    def _on_movement(self, magnitude: float) -> None:
        self._last_movement = magnitude
        if self._state == _ST_STIMULUS and magnitude > _MOTION_THRESHOLD:
            self._record_reaction()

    def _on_punch(self, data: Dict[str, Any]) -> None:
        if self._state == _ST_STIMULUS:
            self._record_reaction()

    def _record_reaction(self) -> None:
        if self._state != _ST_STIMULUS:
            return
        ms = (time.monotonic() - self._stimulus_time) * 1000
        self._times.append(ms)
        color = _ms_color(ms)

        # Update trial card
        idx = len(self._times) - 1
        if idx < len(self._trial_cards):
            card = self._trial_cards[idx]
            card.findChild(QLabel, "val").setText(f"{ms:.0f}ms")
            card.findChild(QLabel, "val").setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color}; background: transparent;")
            card.setStyleSheet(f"background-color: {Color.SURFACE}; border-bottom: 3px solid {color}; border-radius: {Size.RADIUS_SM}px;")

        # Show result briefly
        self._state = _ST_RESULT
        self._set_bg(Color.SURFACE)
        self._set_overlay(f"{ms:.0f} ms", size=40, color=color)

        # After 1s, ask user to return to neutral
        QTimer.singleShot(1000, self._ask_neutral)

    def _ask_neutral(self) -> None:
        if self._trial >= _TOTAL_TRIALS:
            # Last trial — show "Stand still" then go to results
            self._state = _ST_NEUTRAL
            self._set_bg(Color.SURFACE)
            self._set_overlay("Stand still...", size=24, color=Color.TEXT_SECONDARY, bold=False)
            self._neutral_still_since = time.monotonic()
        else:
            # More trials — ask them to reset
            self._state = _ST_NEUTRAL
            self._set_bg(Color.SURFACE)
            self._set_overlay(
                f"Return to neutral position\n\nTrial {self._trial + 1} starting soon...",
                size=20, color=Color.TEXT_SECONDARY, bold=False,
            )
            self._neutral_still_since = time.monotonic()

    def _show_results(self) -> None:
        self._state = _ST_DONE
        self._stop_camera()

        avg = sum(self._times) / len(self._times) if self._times else 0
        best = min(self._times) if self._times else 0
        worst = max(self._times) if self._times else 0
        spread = worst - best
        tier_name, tier_color = _tier_for(avg)

        self._avg_lbl.setText(f"{avg:.0f} ms")
        self._avg_lbl.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {tier_color};")
        self._tier_lbl.setText(tier_name)
        self._tier_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: #FFF; background-color: {tier_color}; border-radius: {Size.RADIUS}px;")
        self._s_best.set_value(f"{best:.0f} ms")
        self._s_worst.set_value(f"{worst:.0f} ms")
        self._s_spread.set_value(f"{spread:.0f} ms")

        # Per-attempt breakdown
        for i, w in enumerate(self._breakdown_labels):
            vl = w.findChild(QLabel, "bval")
            if i < len(self._times):
                ms = self._times[i]
                c = _ms_color(ms)
                vl.setText(f"{ms:.0f}ms")
                vl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {c}; background: transparent;")
                w.setStyleSheet(f"background-color: {Color.BG}; border-radius: 6px; border-bottom: 2px solid {c};")
            else:
                vl.setText("--")
                vl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Color.TEXT_DISABLED}; background: transparent;")
                w.setStyleSheet(f"background-color: {Color.BG}; border-radius: 6px;")

        # Save to history
        self._all_history.append(list(self._times))
        self._hist_title.setVisible(len(self._all_history) > 1)
        for i, lbl in enumerate(self._hist_labels):
            rev = len(self._all_history) - 1 - i
            if rev >= 0:
                s = self._all_history[rev]
                sa = sum(s) / len(s)
                lbl.setText(f"{sa:.0f}ms")
                lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {_ms_color(sa)}; background: {Color.BG}; border-radius: 4px; padding: 2px 6px;")
            else:
                lbl.setText("")

        # Save to session tracker
        try:
            from boxbunny_gui.session_tracker import get_tracker
            get_tracker().add_session(
                mode="Performance", duration="Reaction Test",
                punches=str(_TOTAL_TRIALS), score=f"{avg:.0f}ms ({tier_name})",
            )
        except Exception:
            pass

        self._set_overlay("")
        self._set_bg(Color.SURFACE)
        self._results_w.setVisible(True)

    def _abort(self) -> None:
        self._delay_timer.stop()
        self._tick_timer.stop()
        self._stop_camera()
        self._router.back()

    # ── Camera ───────────────────────────────────────────────────────────

    def _start_camera(self) -> None:
        if self._cam_thread is not None:
            return
        self._cam_worker = _ReactionCameraWorker()
        self._cam_thread = QThread()
        self._cam_worker.moveToThread(self._cam_thread)
        self._cam_worker.frame_ready.connect(self._on_frame)
        self._cam_worker.movement_detected.connect(self._on_movement)
        self._cam_thread.started.connect(self._cam_worker.start_capture)
        self._cam_thread.start()

    def _stop_camera(self) -> None:
        if self._cam_worker:
            self._cam_worker.stop_capture()
        if self._cam_thread:
            self._cam_thread.quit()
            self._cam_thread.wait(2000)
            self._cam_thread = None
            self._cam_worker = None

    def _on_frame(self, qimg: QImage) -> None:
        scaled = qimg.scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video_label.setPixmap(QPixmap.fromImage(scaled))

    # ── Lifecycle ────────────────────────────────────────────────────────

    def on_enter(self, **kwargs: Any) -> None:
        self._state = _ST_IDLE
        self._times.clear()
        self._trial = 0
        self._btn_start.setVisible(True)
        self._results_w.setVisible(False)
        self._trial_badge.setText(f"0 / {_TOTAL_TRIALS}")
        self._trial_badge.setStyleSheet(badge_style(Color.WARNING))
        self._set_bg(Color.SURFACE)
        self._set_overlay("Tap Start to begin", size=26, color=Color.TEXT_SECONDARY)
        self._reset_cards()
        # Start camera immediately so user sees themselves
        self._start_camera()

    def on_leave(self) -> None:
        self._delay_timer.stop()
        self._tick_timer.stop()
        self._stop_camera()


def _centered_label(text: str, size: int, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"font-size: {size}px; font-weight: 600; color: {color}; background: transparent;")
    return lbl
