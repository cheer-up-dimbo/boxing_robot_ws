"""Developer mode overlay widget for BoxBunny.

Shows a visual model of the boxing robot with pads and arms that light up
in real-time as IMU impacts are detected and CV predictions are made.
Toggle via Settings > Developer Mode.

Layout mirrors physical hardware:
            [HEAD PAD]
 [L ARM]  [LEFT] [CENTRE] [RIGHT]  [R ARM]

Pads are rounded rectangles, arms are long vertical pool-noodle rectangles.
Each element lights up on impact/prediction with color indicating force/type.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget

from boxbunny_gui.theme import Color, Size

logger = logging.getLogger(__name__)

# Pad flash duration in ms
FLASH_DURATION_MS = 400

# Force level colors
FORCE_COLORS = {
    "light": QColor("#4CAF50"),    # green
    "medium": QColor("#FF9800"),   # orange
    "hard": QColor("#FF1744"),     # red
}

# Punch type colors for CV predictions
PUNCH_COLORS = {
    "jab": QColor("#42A5F5"),       # blue
    "cross": QColor("#EF5350"),     # red
    "left_hook": QColor("#66BB6A"), # green
    "right_hook": QColor("#FFA726"),# orange
    "left_uppercut": QColor("#AB47BC"),  # purple
    "right_uppercut": QColor("#FFEE58"), # yellow
    "block": QColor("#78909C"),     # grey
    "idle": QColor("#333333"),      # dark
}

INACTIVE_COLOR = QColor("#2A2A2A")
BORDER_COLOR = QColor("#444444")


class DevOverlay(QWidget):
    """Developer mode visual model of the boxing robot hardware.

    Shows pads and arms that flash when IMU impacts or CV predictions occur.
    Displays the predicted punch type and confidence below the model.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(320, 220)
        self._visible = False

        # Pad flash state: pad_name -> (color, expire_time)
        self._pad_flash: Dict[str, tuple] = {}
        # Arm flash state: arm_name -> (color, expire_time)
        self._arm_flash: Dict[str, tuple] = {}
        # Current CV prediction
        self._prediction = "idle"
        self._prediction_conf = 0.0

        # Refresh timer
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def set_developer_mode(self, enabled: bool) -> None:
        """Toggle developer mode visibility."""
        self._visible = enabled
        self.setVisible(enabled)
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()

    def flash_pad(self, pad: str, level: str = "medium") -> None:
        """Flash a pad on impact. pad: left/centre/right/head."""
        color = FORCE_COLORS.get(level, FORCE_COLORS["medium"])
        self._pad_flash[pad] = (color, time.time() + FLASH_DURATION_MS / 1000)
        self.update()

    def flash_arm(self, arm: str, struck: bool = True) -> None:
        """Flash an arm on strike. arm: left/right."""
        color = QColor("#FF1744") if struck else QColor("#4CAF50")
        self._arm_flash[arm] = (color, time.time() + FLASH_DURATION_MS / 1000)
        self.update()

    def set_prediction(self, punch_type: str, confidence: float) -> None:
        """Update the displayed CV prediction."""
        self._prediction = punch_type
        self._prediction_conf = confidence
        self.update()

    def _tick(self) -> None:
        """Clear expired flashes."""
        now = time.time()
        changed = False
        for key in list(self._pad_flash):
            if self._pad_flash[key][1] < now:
                del self._pad_flash[key]
                changed = True
        for key in list(self._arm_flash):
            if self._arm_flash[key][1] < now:
                del self._arm_flash[key]
                changed = True
        if changed:
            self.update()

    def paintEvent(self, event) -> None:
        """Draw the robot model with pads and arms."""
        if not self._visible:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Layout constants
        cx, cy = 160, 85  # center of pad area
        pad_w, pad_h = 50, 50
        pad_gap = 8
        arm_w, arm_h = 24, 90

        # Background panel
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#111111"))
        p.drawRoundedRect(0, 0, 320, 220, 12, 12)

        # Title
        p.setPen(QColor(Color.TEXT_SECONDARY))
        p.setFont(QFont("Inter", 10))
        p.drawText(QRectF(0, 4, 320, 16), Qt.AlignCenter, "DEV MODE — Hardware Visualizer")

        # --- Head pad (top center) ---
        head_x = cx - pad_w // 2
        head_y = cy - pad_h - pad_gap - pad_h // 2
        self._draw_pad(p, head_x, head_y, pad_w, pad_h, "head", "HEAD")

        # --- Bottom row: LEFT, CENTRE, RIGHT ---
        row_y = cy
        left_x = cx - pad_w * 1.5 - pad_gap
        centre_x = cx - pad_w // 2
        right_x = cx + pad_w * 0.5 + pad_gap

        self._draw_pad(p, left_x, row_y, pad_w, pad_h, "left", "L")
        self._draw_pad(p, centre_x, row_y, pad_w, pad_h, "centre", "C")
        self._draw_pad(p, right_x, row_y, pad_w, pad_h, "right", "R")

        # --- Arms (tall rectangles on sides) ---
        arm_y = cy - 10
        left_arm_x = left_x - arm_w - pad_gap * 2
        right_arm_x = right_x + pad_w + pad_gap * 2

        self._draw_arm(p, left_arm_x, arm_y, arm_w, arm_h, "left", "L\nA\nR\nM")
        self._draw_arm(p, right_arm_x, arm_y, arm_w, arm_h, "right", "R\nA\nR\nM")

        # --- Prediction display ---
        pred_y = 170
        pred_color = PUNCH_COLORS.get(self._prediction, PUNCH_COLORS["idle"])
        p.setPen(Qt.NoPen)
        p.setBrush(pred_color)
        p.drawRoundedRect(QRectF(60, pred_y, 200, 28), 6, 6)

        p.setPen(QColor("#000000") if self._prediction != "idle" else QColor(Color.TEXT_SECONDARY))
        p.setFont(QFont("Inter", 12, QFont.Bold))
        conf_str = f"{self._prediction_conf:.0%}" if self._prediction != "idle" else ""
        p.drawText(
            QRectF(60, pred_y, 200, 28), Qt.AlignCenter,
            f"{self._prediction.upper()}  {conf_str}"
        )

        # Force legend
        p.setFont(QFont("Inter", 8))
        p.setPen(QColor(Color.TEXT_SECONDARY))
        legend_y = 202
        for i, (level, color) in enumerate(FORCE_COLORS.items()):
            lx = 60 + i * 90
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(lx, legend_y, 8, 8)
            p.setPen(QColor(Color.TEXT_SECONDARY))
            p.drawText(lx + 12, legend_y + 8, level.capitalize())

        p.end()

    def _draw_pad(
        self, p: QPainter, x: float, y: float, w: float, h: float,
        pad_name: str, label: str
    ) -> None:
        """Draw a single pad rectangle."""
        flash = self._pad_flash.get(pad_name)
        if flash:
            color = flash[0]
        else:
            color = INACTIVE_COLOR

        p.setPen(QPen(BORDER_COLOR, 1.5))
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x, y, w, h), 8, 8)

        p.setPen(QColor("#FFFFFF") if flash else QColor(Color.TEXT_SECONDARY))
        p.setFont(QFont("Inter", 11, QFont.Bold))
        p.drawText(QRectF(x, y, w, h), Qt.AlignCenter, label)

    def _draw_arm(
        self, p: QPainter, x: float, y: float, w: float, h: float,
        arm_name: str, label: str
    ) -> None:
        """Draw a robot arm (pool noodle rectangle)."""
        flash = self._arm_flash.get(arm_name)
        if flash:
            color = flash[0]
        else:
            color = QColor("#1E1E1E")

        p.setPen(QPen(BORDER_COLOR, 1.5))
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x, y, w, h), 6, 6)

        p.setPen(QColor("#FFFFFF") if flash else QColor("#555555"))
        p.setFont(QFont("Inter", 7))
        p.drawText(QRectF(x, y, w, h), Qt.AlignCenter, label)
