"""IMU pad navigation handler.

Translates NavCommand strings (from ROS or keyboard fallback) into
Qt signals that the router and active page can consume.

Keyboard fallback (for desktop development):
  Left / Right arrows  ->  navigate_prev / navigate_next
  Enter / Return       ->  select
  Escape               ->  go_back
"""
from __future__ import annotations

import logging
from typing import Optional, Set

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# Session states in which IMU navigation is disabled
_DISABLED_STATES: Set[str] = {"countdown", "active"}


class ImuNavHandler(QObject):
    """Translates IMU pad hits and keyboard keys into navigation signals."""

    navigate_prev = Signal()
    navigate_next = Signal()
    select = Signal()
    go_back = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._enabled: bool = True
        self._keyboard_enabled: bool = True
        self._session_state: str = "idle"

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled and self._session_state not in _DISABLED_STATES

    def set_enabled(self, enabled: bool) -> None:
        """Master enable/disable (e.g. from settings checkbox)."""
        self._enabled = enabled
        logger.debug("IMU nav enabled: %s", enabled)

    def set_keyboard_enabled(self, enabled: bool) -> None:
        """Enable/disable keyboard fallback."""
        self._keyboard_enabled = enabled

    def on_session_state_changed(self, state: str, _mode: str) -> None:
        """Called when session state changes.  Disables nav during active play."""
        self._session_state = state
        logger.debug("IMU nav session state: %s (nav active: %s)", state, self.enabled)

    # ── ROS command ingestion ───────────────────────────────────────────

    def handle_command(self, command: str) -> None:
        """Process a NavCommand string from the ROS bridge."""
        if not self.enabled:
            return
        command = command.strip().lower()
        if command == "prev":
            self.navigate_prev.emit()
        elif command == "next":
            self.navigate_next.emit()
        elif command == "enter":
            self.select.emit()
        elif command == "back":
            self.go_back.emit()
        else:
            logger.warning("Unknown nav command: '%s'", command)

    # ── Keyboard fallback ───────────────────────────────────────────────

    def handle_key(self, event: QKeyEvent) -> bool:
        """Process a Qt key event.  Returns True if the event was consumed."""
        if not self._keyboard_enabled or not self.enabled:
            return False

        key = event.key()
        if key == Qt.Key.Key_Left:
            self.navigate_prev.emit()
            return True
        if key == Qt.Key.Key_Right:
            self.navigate_next.emit()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.select.emit()
            return True
        if key == Qt.Key.Key_Escape:
            self.go_back.emit()
            return True
        return False


class KeyboardNavFilter(QObject):
    """Event filter that forwards key presses to an ImuNavHandler.

    Install on the top-level QWidget so that keyboard navigation works
    even during development without an IMU.
    """

    def __init__(self, handler: ImuNavHandler, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._handler = handler

    def eventFilter(self, obj: QObject, event: object) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
            if self._handler.handle_key(event):
                return True
        return super().eventFilter(obj, event)
