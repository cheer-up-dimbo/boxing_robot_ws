"""Guest home page shown after the skill assessment.

Recommended drill card at top, 2x2 mode grid, QR to save progress.
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

from boxbunny_gui.theme import Color, Size, font, GHOST_BTN
from boxbunny_gui.widgets import BigButton, QRWidget

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_MODES = [
    ("Training", "combo_select"),
    ("Sparring", "sparring_config"),
    ("Free Training", "training_config"),
    ("Performance", "performance_menu"),
]

_DIFFICULTY_MAP = {"Light": "beginner", "Medium": "intermediate", "Hard": "advanced"}


class _ModeCard(QFrame):
    """Touchable card for a training mode."""

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
        lbl = QLabel(label)
        lbl.setFont(font(20, bold=True))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)


class HomeGuestPage(QWidget):
    """Dashboard for a guest (unauthenticated) user."""

    def __init__(self, router: PageRouter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Size.SPACING, Size.SPACING_SM, Size.SPACING, Size.SPACING_SM)
        root.setSpacing(Size.SPACING)

        # Top bar
        top = QHBoxLayout()
        guest_lbl = QLabel("Guest")
        guest_lbl.setFont(font(22, bold=True))
        top.addWidget(guest_lbl)
        top.addStretch()
        self._qr_top = QRWidget(data="https://boxbunny.local/signup", size=48)
        top.addWidget(self._qr_top)
        save_lbl = QLabel("Scan to save progress")
        save_lbl.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; font-size: 13px;")
        top.addWidget(save_lbl)
        root.addLayout(top)

        # Recommended card
        self._rec_card = QFrame()
        self._rec_card.setFixedHeight(90)
        self._rec_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rec_card.setStyleSheet(
            f"QFrame {{ background-color: {Color.SURFACE};"
            f" border: 2px solid {Color.PRIMARY};"
            f" border-radius: {Size.RADIUS_LG}px; }}"
        )
        rec_lay = QVBoxLayout(self._rec_card)
        self._rec_title = QLabel("Recommended for You")
        self._rec_title.setFont(font(16, bold=True))
        self._rec_title.setStyleSheet(f"color: {Color.PRIMARY};")
        self._rec_desc = QLabel("Jab-Cross Combo -- Beginner")
        self._rec_desc.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; font-size: 14px;")
        rec_lay.addWidget(self._rec_title)
        rec_lay.addWidget(self._rec_desc)
        self._rec_card.mousePressEvent = lambda _e: self._router.navigate("combo_select")
        root.addWidget(self._rec_card)

        # 2x2 mode grid
        grid = QGridLayout()
        grid.setSpacing(Size.SPACING)
        for i, (label, route) in enumerate(_MODES):
            card = _ModeCard(label, self)
            card.mousePressEvent = lambda _e, r=route: self._router.navigate(r)
            grid.addWidget(card, i // 2, i % 2)
        root.addLayout(grid)

        root.addStretch()

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        experience = kwargs.get("experience", "No")
        goal = kwargs.get("goal", "Fitness")
        intensity = kwargs.get("intensity", "Light")
        difficulty = _DIFFICULTY_MAP.get(intensity, "beginner")

        # Pick a recommendation based on assessment
        if experience == "No":
            rec_text = f"Jab-Cross Combo -- {difficulty.title()}"
        else:
            rec_text = f"Jab-Cross-Hook-Cross -- {difficulty.title()}"
        self._rec_desc.setText(rec_text)
        logger.debug("HomeGuestPage entered (goal=%s, intensity=%s)", goal, intensity)

    def on_leave(self) -> None:
        pass
