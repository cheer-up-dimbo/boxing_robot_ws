"""Collapsible AI coaching-tip bar that slides down from the top.

Displays coaching feedback with a coloured left accent bar.
Auto-collapses after 10 seconds.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, GHOST_BTN

log = logging.getLogger(__name__)

_BAR_HEIGHT = 60
_ACCENT_COLORS: dict[str, str] = {
    "info": Color.PRIMARY,
    "warning": Color.WARNING,
    "danger": Color.DANGER,
}


class CoachTipBar(QWidget):
    """Full-width top bar showing a coaching tip with slide animation.

    Signals
    -------
    dismissed
        Emitted when the tip is collapsed (manually or by auto-timer).
    """

    dismissed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # -- inner frame -------------------------------------------------------
        self._frame = QFrame(self)
        self._frame.setStyleSheet(
            f"QFrame {{ background-color: {Color.SURFACE};"
            f" border-radius: {Size.RADIUS}px; }}"
        )
        frame_layout = QHBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 8, 0)
        frame_layout.setSpacing(Size.SPACING_SM)

        # accent bar
        self._accent = QFrame()
        self._accent.setFixedWidth(4)
        self._accent.setStyleSheet(f"background-color: {Color.PRIMARY}; border-radius: 2px;")

        # coach icon placeholder
        self._icon_lbl = QLabel("\U0001F3AF")
        self._icon_lbl.setFixedSize(32, 32)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")

        # tip text
        self._text_lbl = QLabel("")
        self._text_lbl.setWordWrap(True)
        self._text_lbl.setStyleSheet(
            f"color: {Color.TEXT}; font-size: 14px; background: transparent;"
        )
        self._text_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # collapse / expand toggle
        self._toggle_btn = QPushButton("\u2715")
        self._toggle_btn.setFixedSize(Size.MIN_TOUCH, 36)
        self._toggle_btn.setStyleSheet(GHOST_BTN)
        self._toggle_btn.clicked.connect(self.collapse)

        frame_layout.addWidget(self._accent)
        frame_layout.addWidget(self._icon_lbl)
        frame_layout.addWidget(self._text_lbl, 1)
        frame_layout.addWidget(self._toggle_btn)

        # -- animations --------------------------------------------------------
        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # auto-collapse timer
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.setInterval(10_000)
        self._auto_timer.timeout.connect(self.collapse)

    # -- public API -----------------------------------------------------------
    def show_tip(self, text: str, tip_type: str = "info") -> None:
        """Show a coaching tip.

        Parameters
        ----------
        text : str
            The tip text.
        tip_type : str
            ``"info"`` (green), ``"warning"`` (orange), or ``"danger"`` (red).
        """
        accent_color = _ACCENT_COLORS.get(tip_type, Color.PRIMARY)
        self._accent.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
        self._text_lbl.setText(text)
        self.expand()
        self._auto_timer.start()

    def collapse(self) -> None:
        """Animate the bar closed."""
        self._auto_timer.stop()
        self._anim.stop()
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(0)
        self._anim.start()
        self.dismissed.emit()

    def expand(self) -> None:
        """Animate the bar open."""
        self._anim.stop()
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(_BAR_HEIGHT)
        self._anim.start()

    # -- geometry bookkeeping -------------------------------------------------
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._frame.setGeometry(0, 0, self.width(), _BAR_HEIGHT)
