"""Reaction time test page.

Random-delay stimulus (green screen flash), 3 trials, results with
tier classification. Uses YOLO pose estimation for motion detection
with live camera feed, plus IMU punch as backup trigger.
"""
from __future__ import annotations

import logging
import random
import sys
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

from boxbunny_gui.theme import Color, Icon, Size, font, badge_style, back_link_style, GHOST_BTN, PRIMARY_BTN
from boxbunny_gui.widgets import BigButton, StatCard

if TYPE_CHECKING:
    from boxbunny_gui.gui_bridge import GuiBridge
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_TOTAL_TRIALS = 3
_MIN_DELAY_MS = 1000
_MAX_DELAY_MS = 4000
_MOTION_THRESHOLD = 20.0  # pixels keypoint displacement

_TIERS = [
    (150, "Lightning"),
    (200, "Fast"),
    (280, "Average"),
    (380, "Developing"),
    (9999, "Slow"),
]

# Path to YOLO pose model
_WS_ROOT = Path(__file__).resolve().parents[5]
_YOLO_POSE_PATH = _WS_ROOT / "action_prediction" / "model" / "yolo26n-pose.pt"


class _ReactionCameraWorker(QObject):
    """Background worker for camera capture + YOLO pose estimation.

    Runs in a QThread, emits frames and movement detection signals.
    Uses the lightweight YOLO pose model (NOT the heavy voxelflow engine).
    """

    frame_ready = Signal(object)        # QImage
    movement_detected = Signal(float)   # movement magnitude in pixels

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._model = None
        self._prev_keypoints = None

    def start_capture(self) -> None:
        """Start the capture + pose loop."""
        self._running = True
        self._prev_keypoints = None

        # Try to import YOLO and load model
        try:
            from ultralytics import YOLO
            model_path = str(_YOLO_POSE_PATH) if _YOLO_POSE_PATH.exists() else "yolo11s-pose.pt"
            self._model = YOLO(model_path)
            logger.info("Reaction pose model loaded: %s", model_path)
        except Exception as e:
            logger.warning("Failed to load YOLO pose: %s (camera-only mode)", e)
            self._model = None

        # Try RealSense first, fall back to cv2.VideoCapture
        cap = None
        try:
            import pyrealsense2 as rs
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            pipeline.start(config)
            logger.info("RealSense camera opened for reaction test")
            self._run_realsense(pipeline)
            pipeline.stop()
            return
        except Exception:
            pass

        # Fallback to OpenCV camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Cannot open camera for reaction test")
            self._running = False
            return

        logger.info("OpenCV camera opened for reaction test")
        try:
            self._run_opencv(cap)
        finally:
            cap.release()

    def stop_capture(self) -> None:
        self._running = False

    def _run_realsense(self, pipeline) -> None:
        import pyrealsense2 as rs
        while self._running:
            frames = pipeline.wait_for_frames(timeout_ms=100)
            color = frames.get_color_frame()
            if not color:
                continue
            bgr = np.asanyarray(color.get_data())
            self._process_frame(bgr)

    def _run_opencv(self, cap) -> None:
        while self._running:
            ok, bgr = cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            bgr = cv2.flip(bgr, 1)
            self._process_frame(bgr)

    def _process_frame(self, bgr: np.ndarray) -> None:
        """Run pose estimation and emit signals."""
        display = bgr.copy()
        movement = 0.0

        if self._model is not None:
            try:
                results = self._model(bgr, verbose=False)
                kps = self._extract_keypoints(results)
                if kps is not None:
                    # Draw skeleton on display
                    self._draw_skeleton(display, kps)
                    # Compute movement
                    if self._prev_keypoints is not None:
                        movement = self._compute_motion(self._prev_keypoints, kps)
                    self._prev_keypoints = kps
            except Exception:
                pass

        # Convert BGR to RGB QImage
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.frame_ready.emit(qimg)

        if movement > 0:
            self.movement_detected.emit(movement)

    @staticmethod
    def _extract_keypoints(results):
        if not results or len(results) == 0:
            return None
        kps = results[0].keypoints
        if kps is None or kps.data is None:
            return None
        arr = kps.data.cpu().numpy()
        if arr.shape[0] == 0:
            return None
        return arr[0]

    @staticmethod
    def _compute_motion(prev, curr, conf_threshold: float = 0.3) -> float:
        max_dist = 0.0
        for i in range(min(len(prev), len(curr))):
            p, c = prev[i], curr[i]
            if len(p) >= 3 and len(c) >= 3:
                if p[2] < conf_threshold or c[2] < conf_threshold:
                    continue
            dist = float(np.sqrt((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2))
            max_dist = max(max_dist, dist)
        return max_dist

    @staticmethod
    def _draw_skeleton(img: np.ndarray, kps: np.ndarray) -> None:
        """Draw keypoint dots on the image."""
        for i in range(len(kps)):
            x, y = int(kps[i][0]), int(kps[i][1])
            conf = kps[i][2] if len(kps[i]) >= 3 else 1.0
            if conf > 0.3:
                cv2.circle(img, (x, y), 4, (0, 255, 0), -1)


class ReactionTestPage(QWidget):
    """3-trial reaction time test with camera feed and pose detection."""

    def __init__(
        self,
        router: PageRouter,
        bridge: Optional[GuiBridge] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._router = router
        self._bridge = bridge
        self._trial: int = 0
        self._times: List[float] = []
        self._stimulus_on: bool = False
        self._stimulus_time: float = 0.0
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._show_stimulus)

        # Camera worker
        self._cam_thread: Optional[QThread] = None
        self._cam_worker: Optional[_ReactionCameraWorker] = None

        self._build_ui()
        if self._bridge:
            self._bridge.punch_confirmed.connect(self._on_punch)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, Size.SPACING_SM, 30, 22)
        root.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        btn_back = _QPushButton(f"{Icon.BACK}  Back")
        btn_back.setStyleSheet(back_link_style())
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self._abort)
        top.addWidget(btn_back)
        self._title = QLabel("Reaction Time")
        self._title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Color.TEXT};")
        top.addWidget(self._title)
        top.addStretch()
        self._trial_lbl = QLabel(f"Trial 0/{_TOTAL_TRIALS}")
        self._trial_lbl.setStyleSheet(badge_style(Color.WARNING))
        top.addWidget(self._trial_lbl)
        root.addLayout(top)

        # Stimulus area with camera feed underneath
        self._stimulus = QWidget()
        self._stimulus.setMinimumHeight(200)
        stim_stack = QStackedLayout(self._stimulus)
        stim_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Layer 0: Camera feed
        self._video_label = QLabel()
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setStyleSheet(
            f"background-color: {Color.SURFACE};"
            f" border-radius: 14px;"
        )
        stim_stack.addWidget(self._video_label)

        # Layer 1: Text overlay
        self._stimulus_lbl = QLabel("Tap Start to begin")
        self._stimulus_lbl.setFont(font(28, bold=True))
        self._stimulus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stimulus_lbl.setWordWrap(True)
        self._stimulus_lbl.setStyleSheet(
            f"background: transparent; color: {Color.TEXT_SECONDARY};"
            " font-size: 28px; font-weight: 700;"
        )
        stim_stack.addWidget(self._stimulus_lbl)

        self._set_stimulus_bg(Color.SURFACE)
        root.addWidget(self._stimulus, stretch=1)

        root.addSpacing(10)

        # Trial indicators row
        trials_row = QHBoxLayout()
        trials_row.setSpacing(12)
        trials_row.addStretch()
        self._trial_cards: list[QLabel] = []
        for i in range(_TOTAL_TRIALS):
            card = QLabel(f"#{i + 1}")
            card.setFixedSize(90, 40)
            card.setAlignment(Qt.AlignCenter)
            card.setStyleSheet(f"""
                font-size: 13px; font-weight: 600; color: {Color.TEXT_DISABLED};
                background-color: #131920;
                border: 1px solid #1E2832;
                border-radius: {Size.RADIUS_SM}px;
            """)
            trials_row.addWidget(card)
            self._trial_cards.append(card)
        trials_row.addStretch()
        root.addLayout(trials_row)

        root.addSpacing(10)

        # Start button
        self._btn_start = BigButton("Start", stylesheet=PRIMARY_BTN)
        self._btn_start.setFixedHeight(70)
        self._btn_start.clicked.connect(self._begin_test)
        root.addWidget(self._btn_start)

        # Results panel
        self._results_widget = QWidget()
        res_lay = QVBoxLayout(self._results_widget)
        res_lay.setSpacing(12)
        res_lay.setContentsMargins(0, 4, 0, 0)

        res_title = QLabel("Results")
        res_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        res_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {Color.TEXT};"
            " background-color: #1A1810;"
            " border: 1px solid #3D351A;"
            f" border-radius: {Size.RADIUS}px;"
            " padding: 10px 20px;"
        )
        res_lay.addWidget(res_title)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        self._stat_avg = StatCard("Average", "-- ms", accent=Color.PRIMARY)
        self._stat_best = StatCard("Best", "-- ms", accent=Color.PRIMARY_LIGHT)
        self._stat_worst = StatCard("Worst", "-- ms", accent=Color.DANGER)
        self._stat_tier = StatCard("Tier", "--", accent=Color.WARNING)
        stats.addWidget(self._stat_avg)
        stats.addWidget(self._stat_best)
        stats.addWidget(self._stat_worst)
        stats.addWidget(self._stat_tier)
        res_lay.addLayout(stats)

        btn_done = BigButton("Done", stylesheet=PRIMARY_BTN)
        btn_done.setFixedHeight(70)
        btn_done.clicked.connect(
            lambda: self._router.navigate("performance")
        )
        res_lay.addWidget(btn_done)
        self._results_widget.setVisible(False)
        root.addWidget(self._results_widget)

    def _set_stimulus_bg(self, color: str) -> None:
        border = Color.BORDER if color == Color.SURFACE else color
        self._video_label.setStyleSheet(
            f"background-color: {color};"
            f" border-radius: 14px;"
            f" border: 2px solid {border};"
        )

    def _reset_trial_cards(self) -> None:
        for i, card in enumerate(self._trial_cards):
            card.setText(f"#{i + 1}")
            card.setStyleSheet(f"""
                font-size: 13px; font-weight: 600; color: {Color.TEXT_DISABLED};
                background-color: #131920;
                border: 1px solid #1E2832;
                border-radius: {Size.RADIUS_SM}px;
            """)

    def imu_start(self) -> None:
        if self._btn_start.isVisible():
            self._begin_test()

    def _begin_test(self) -> None:
        self._trial = 0
        self._times.clear()
        self._reset_trial_cards()
        self._btn_start.setVisible(False)
        self._results_widget.setVisible(False)
        self._start_camera()
        self._next_trial()

    def _next_trial(self) -> None:
        self._trial += 1
        self._trial_lbl.setText(f"Trial {self._trial}/{_TOTAL_TRIALS}")
        self._stimulus_on = False
        self._set_stimulus_bg(Color.SURFACE)
        self._stimulus_lbl.setText("Wait for green...")
        self._stimulus_lbl.setStyleSheet(
            f"background: transparent; color: {Color.TEXT_DISABLED}; font-size: 32px; font-weight: 700;"
            " letter-spacing: 1px;"
        )
        delay = random.randint(_MIN_DELAY_MS, _MAX_DELAY_MS)
        self._delay_timer.start(delay)

    def _show_stimulus(self) -> None:
        self._stimulus_on = True
        self._stimulus_time = time.monotonic()
        # Reset pose baseline for fresh motion detection
        if self._cam_worker:
            self._cam_worker._prev_keypoints = None
        self._set_stimulus_bg(Color.SUCCESS)
        self._stimulus_lbl.setText("PUNCH NOW!")
        self._stimulus_lbl.setStyleSheet(
            "background: transparent; color: #FFFFFF; font-size: 44px; font-weight: 800;"
            " letter-spacing: 2px;"
        )

    def _on_movement(self, magnitude: float) -> None:
        """Pose-based reaction detection."""
        if not self._stimulus_on:
            return
        if magnitude > _MOTION_THRESHOLD:
            self._record_reaction()

    def _on_punch(self, data: Dict[str, Any]) -> None:
        """IMU punch backup trigger."""
        if not self._stimulus_on:
            return
        self._record_reaction()

    def _record_reaction(self) -> None:
        """Record a successful reaction (from either pose or IMU)."""
        if not self._stimulus_on:
            return
        reaction_ms = (time.monotonic() - self._stimulus_time) * 1000
        self._times.append(reaction_ms)
        self._stimulus_on = False
        self._set_stimulus_bg(Color.SURFACE)
        self._stimulus_lbl.setText(f"{reaction_ms:.0f} ms")
        self._stimulus_lbl.setStyleSheet(
            f"background: transparent; color: {Color.PRIMARY}; font-size: 44px; font-weight: 800;"
        )

        idx = len(self._times) - 1
        if idx < len(self._trial_cards):
            ms = reaction_ms
            if ms < 200:
                color = Color.SUCCESS
            elif ms < 350:
                color = Color.PRIMARY
            else:
                color = Color.DANGER
            self._trial_cards[idx].setText(f"{ms:.0f}ms")
            self._trial_cards[idx].setStyleSheet(f"""
                font-size: 13px; font-weight: 700; color: {color};
                background-color: #131920;
                border: 1px solid {color};
                border-radius: {Size.RADIUS_SM}px;
            """)

        if self._trial >= _TOTAL_TRIALS:
            QTimer.singleShot(800, self._show_results)
        else:
            QTimer.singleShot(800, self._next_trial)

    def _show_results(self) -> None:
        self._stop_camera()
        avg = sum(self._times) / len(self._times) if self._times else 0
        best = min(self._times) if self._times else 0
        worst = max(self._times) if self._times else 0
        tier = next((t for ms, t in _TIERS if avg <= ms), "Slow")

        self._stat_avg.set_value(f"{avg:.0f} ms")
        self._stat_best.set_value(f"{best:.0f} ms")
        self._stat_worst.set_value(f"{worst:.0f} ms")
        self._stat_tier.set_value(tier)
        self._results_widget.setVisible(True)
        self._stimulus_lbl.setText("Test Complete")
        self._stimulus_lbl.setStyleSheet(
            f"background: transparent; color: {Color.PRIMARY}; font-size: 28px; font-weight: 700;"
        )

    def _abort(self) -> None:
        self._delay_timer.stop()
        self._stop_camera()
        self._router.back()

    # ── Camera worker management ──────────────────────────────────────

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
        """Display camera frame in the video label."""
        scaled = qimg.scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video_label.setPixmap(QPixmap.fromImage(scaled))

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._times.clear()
        self._trial = 0
        self._stimulus_on = False
        self._btn_start.setVisible(True)
        self._results_widget.setVisible(False)
        self._trial_lbl.setText(f"Trial 0/{_TOTAL_TRIALS}")
        self._trial_lbl.setStyleSheet(badge_style(Color.WARNING))
        self._set_stimulus_bg(Color.SURFACE)
        self._stimulus_lbl.setText("Tap Start to begin")
        self._stimulus_lbl.setStyleSheet(
            f"background: transparent; color: {Color.TEXT_SECONDARY}; font-size: 28px; font-weight: 700;"
        )
        self._reset_trial_cards()
        logger.debug("ReactionTestPage entered")

    def on_leave(self) -> None:
        self._delay_timer.stop()
        self._stop_camera()
