"""Logged-in user home page.

Top bar with username/level, preset favourites row, 2x2 mode grid,
and bottom row with History and QR buttons.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, GHOST_BTN, SURFACE_BTN
from boxbunny_gui.widgets import BigButton, PresetCard, QRWidget

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_MODES = [
    ("Training", "combo_select"),
    ("Sparring", "sparring_config"),
    ("Free Training", "training_config"),
    ("Performance", "performance_menu"),
]


class _ModeCard(QFrame):
    """Large touchable card for a training mode."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(230, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QFrame {{ background-color: {Color.SURFACE};"
            f" border-radius: {Size.RADIUS_LG}px; }}"
            f" QFrame:hover {{ background-color: {Color.SURFACE_HOVER}; }}"
        )
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # TODO: add icon placeholder above label
        lbl = QLabel(label)
        lbl.setFont(font(20, bold=True))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)


class HomeIndividualPage(QWidget):
    """Dashboard for an authenticated user."""

    def __init__(self, router: PageRouter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._user_id: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Size.SPACING, Size.SPACING_SM, Size.SPACING, Size.SPACING_SM)
        root.setSpacing(Size.SPACING)

        # Top bar
        top = QHBoxLayout()
        self._user_lbl = QLabel("User")
        self._user_lbl.setFont(font(22, bold=True))
        top.addWidget(self._user_lbl)
        self._level_lbl = QLabel("Beginner")
        self._level_lbl.setStyleSheet(
            f"color: {Color.PRIMARY}; font-size: 14px;"
            f" background-color: {Color.SURFACE}; border-radius: 8px; padding: 4px 10px;"
        )
        top.addWidget(self._level_lbl)
        top.addStretch()
        self._btn_settings = BigButton("Settings", stylesheet=GHOST_BTN)
        self._btn_settings.setFixedWidth(100)
        self._btn_settings.clicked.connect(lambda: self._router.navigate("settings"))
        top.addWidget(self._btn_settings)
        root.addLayout(top)

        # Preset favourites row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(Size.SPACING)
        for i in range(3):
            card = PresetCard(name=f"Preset {i+1}", parent=self)
            card.clicked.connect(lambda _c=False, idx=i: self._on_preset(idx))
            preset_row.addWidget(card)
        preset_row.addStretch()
        root.addLayout(preset_row)

        # 2x2 mode grid
        grid = QGridLayout()
        grid.setSpacing(Size.SPACING)
        for i, (label, route) in enumerate(_MODES):
            card = _ModeCard(label, self)
            card.mousePressEvent = lambda _e, r=route: self._router.navigate(r)
            grid.addWidget(card, i // 2, i % 2)
        root.addLayout(grid)

        root.addStretch()

        # Bottom row
        bottom = QHBoxLayout()
        self._btn_history = BigButton("History", stylesheet=SURFACE_BTN)
        self._btn_history.setFixedWidth(Size.BUTTON_W_SM)
        self._btn_history.clicked.connect(lambda: self._router.navigate("history"))
        bottom.addWidget(self._btn_history)
        bottom.addStretch()
        self._qr = QRWidget(data="https://boxbunny.local/dashboard", size=60)
        bottom.addWidget(self._qr)
        root.addLayout(bottom)

    def _on_preset(self, index: int) -> None:
        # TODO: load preset config and navigate to training_config
        logger.info("Preset %d selected", index)

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._user_id = kwargs.get("user_id", "")
        # TODO: load user data from database
        logger.debug("HomeIndividualPage entered (user_id=%s)", self._user_id)

    def on_leave(self) -> None:
        pass
