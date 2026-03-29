"""Startup / landing page -- first screen on boot.

BoxBunny branding with Start Training, Log In, and Coach Login buttons.
IMU navigable: left/right cycles focus, centre selects.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import (
    Color,
    Size,
    font,
    GHOST_BTN,
    PRIMARY_BTN,
    SURFACE_BTN,
)
from boxbunny_gui.widgets import BigButton, QRWidget

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)


class StartupPage(QWidget):
    """Landing screen with branding and three entry-point buttons."""

    def __init__(self, router: PageRouter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._focus_index: int = 0
        self._focusable: list[BigButton] = []
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Branding area (top third) ------------------------------------
        brand = QLabel("BoxBunny")
        brand.setFont(font(42, bold=True))
        brand.setStyleSheet(f"color: {Color.PRIMARY};")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("AI Boxing Trainer")
        subtitle.setFont(font(18))
        subtitle.setStyleSheet(f"color: {Color.TEXT_SECONDARY};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addStretch(2)
        root.addWidget(brand)
        root.addWidget(subtitle)
        root.addStretch(1)

        # -- Main buttons (center) ----------------------------------------
        btn_box = QVBoxLayout()
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_box.setSpacing(Size.SPACING)

        self._btn_start = BigButton("Start Training", stylesheet=PRIMARY_BTN)
        self._btn_start.setFixedWidth(int(Size.SCREEN_W * 0.6))
        self._btn_start.setFixedHeight(80)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_login = BigButton("Log In", stylesheet=SURFACE_BTN)
        self._btn_login.setFixedWidth(int(Size.SCREEN_W * 0.4))
        self._btn_login.clicked.connect(self._on_login)

        btn_box.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignCenter)
        btn_box.addWidget(self._btn_login, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addLayout(btn_box)
        root.addStretch(2)

        # -- Bottom row: QR (left) + Coach Login (right) ------------------
        bottom = QHBoxLayout()
        bottom.setContentsMargins(Size.SPACING, 0, Size.SPACING, Size.SPACING)

        self._qr = QRWidget(data="https://boxbunny.local/dashboard", size=80)
        bottom.addWidget(self._qr, alignment=Qt.AlignmentFlag.AlignLeft)
        bottom.addStretch()

        self._btn_coach = BigButton("Coach Login", stylesheet=GHOST_BTN)
        self._btn_coach.setFixedWidth(160)
        self._btn_coach.clicked.connect(self._on_coach)
        bottom.addWidget(self._btn_coach, alignment=Qt.AlignmentFlag.AlignRight)

        root.addLayout(bottom)

        self._focusable = [self._btn_start, self._btn_login, self._btn_coach]

    # ── Navigation handlers ────────────────────────────────────────────
    def _on_start(self) -> None:
        self._router.navigate("guest_assessment")

    def _on_login(self) -> None:
        self._router.navigate("account_picker")

    def _on_coach(self) -> None:
        self._router.navigate("account_picker", coach_only=True)

    # ── IMU focus cycling ──────────────────────────────────────────────
    def cycle_focus(self, direction: int) -> None:
        """Move focus by *direction* (+1 or -1) among touchable buttons."""
        if not self._focusable:
            return
        for btn in self._focusable:
            btn.set_focused(False)
        self._focus_index = (self._focus_index + direction) % len(self._focusable)
        self._focusable[self._focus_index].set_focused(True)

    def activate_focused(self) -> None:
        """Simulate a click on the currently focused button."""
        if self._focusable:
            self._focusable[self._focus_index].click()

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._focus_index = 0
        logger.debug("StartupPage entered")

    def on_leave(self) -> None:
        for btn in self._focusable:
            btn.set_focused(False)
