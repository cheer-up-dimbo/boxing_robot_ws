"""Large timer display with optional circular progress ring.

Designed to be composable on any page with a transparent background.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from boxbunny_gui.theme import Color, Size

log = logging.getLogger(__name__)


class TimerDisplay(QWidget):
    """Countdown / count-up timer with an optional progress arc.

    Signals
    -------
    finished
        Emitted when the countdown reaches zero.
    tick(int)
        Emitted every second with the remaining seconds.
    """

    finished = Signal()
    tick = Signal(int)

    def __init__(
        self,
        font_size: int = Size.TEXT_TIMER,
        show_ring: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._font_size = font_size
        self._show_ring = show_ring

        self._total: int = 0
        self._remaining: int = 0
        self._running: bool = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # -- public API -----------------------------------------------------------
    def start(self, total_seconds: int) -> None:
        """Begin a countdown from *total_seconds*."""
        self._total = total_seconds
        self._remaining = total_seconds
        self._running = True
        self._timer.start()
        self.update()

    def pause(self) -> None:
        """Pause the countdown."""
        self._running = False
        self._timer.stop()

    def resume(self) -> None:
        """Resume after a pause."""
        if self._remaining > 0:
            self._running = True
            self._timer.start()

    def reset(self) -> None:
        """Stop and zero the timer."""
        self._timer.stop()
        self._running = False
        self._remaining = 0
        self._total = 0
        self.update()

    def set_time(self, seconds: int) -> None:
        """Set the display to an arbitrary value without starting."""
        self._remaining = max(0, seconds)
        self._total = max(self._total, self._remaining)
        self.update()

    # -- internal -------------------------------------------------------------
    def _on_tick(self) -> None:
        self._remaining = max(0, self._remaining - 1)
        self.tick.emit(self._remaining)
        self.update()
        if self._remaining <= 0:
            self._timer.stop()
            self._running = False
            self.finished.emit()

    def _current_color(self) -> str:
        if self._remaining <= 10:
            return Color.DANGER
        if self._remaining <= 30:
            return Color.WARNING
        return Color.PRIMARY

    @staticmethod
    def _format_time(seconds: int) -> str:
        if seconds >= 60:
            m, s = divmod(seconds, 60)
            return f"{m:02d}:{s:02d}"
        return f"{seconds}"

    # -- painting -------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        color_hex = self._current_color()
        color = QColor(color_hex)

        # -- progress ring ----------------------------------------------------
        if self._show_ring and self._total > 0:
            pen_w = 6
            margin = pen_w + 4
            ring_rect = QRect(
                (self.width() - side) // 2 + margin,
                (self.height() - side) // 2 + margin,
                side - 2 * margin,
                side - 2 * margin,
            )

            # background track
            track_pen = QPen(QColor(Color.SURFACE_LIGHT), pen_w)
            track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(track_pen)
            painter.drawArc(ring_rect, 0, 360 * 16)

            # foreground arc (shrinks as time elapses)
            fraction = self._remaining / self._total if self._total else 0
            span = int(fraction * 360 * 16)
            arc_pen = QPen(color, pen_w)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(ring_rect, 90 * 16, span)

        # -- time text --------------------------------------------------------
        painter.setPen(QColor(color_hex))
        painter.setFont(QFont("Inter", self._font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._format_time(self._remaining))
        painter.end()
