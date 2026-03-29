"""Guest home page — shown after skill assessment.

Colorful mode cards filling the screen. Premium, aesthetic design.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from boxbunny_gui.theme import Color, badge_style, close_btn_style, mode_card_style

logger = logging.getLogger(__name__)

_MODES = [
    {
        "name": "Training",
        "desc": "Practice combos with guided drills",
        "accent": Color.PRIMARY,
        "route": "training_select",
    },
    {
        "name": "Sparring",
        "desc": "Fight against the robot AI",
        "accent": Color.DANGER,
        "route": "sparring_select",
    },
    {
        "name": "Free Training",
        "desc": "Open session, no structure",
        "accent": Color.INFO,
        "route": "training_session",
    },
    {
        "name": "Performance",
        "desc": "Test your power, stamina and speed",
        "accent": Color.PURPLE,
        "route": "performance",
    },
]


def _mode_card(mode: dict) -> QPushButton:
    """Large mode card that expands to fill available space."""
    btn = QPushButton()
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(mode_card_style(mode["accent"]))
    btn.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )

    lay = QVBoxLayout(btn)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(6)

    title = QLabel(mode["name"])
    title.setStyleSheet(
        f"font-size: 20px; font-weight: 700; color: {Color.TEXT};"
    )
    title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    lay.addWidget(title)

    desc = QLabel(mode["desc"])
    desc.setStyleSheet(
        f"font-size: 14px; color: {Color.TEXT_SECONDARY};"
    )
    desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    lay.addWidget(desc)

    lay.addStretch()

    return btn


class HomeGuestPage(QWidget):
    """Menu for guest (unauthenticated) users — 2x2 colorful grid."""

    def __init__(self, router=None, **kwargs):
        super().__init__()
        self._router = router

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 16, 32, 16)
        root.setSpacing(12)

        # ── Top bar ──────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(12)
        title = QLabel("Guest Mode")
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {Color.TEXT};"
        )
        top.addWidget(title)

        badge = QLabel("No account")
        badge.setStyleSheet(badge_style())
        top.addWidget(badge)
        top.addStretch()

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet(close_btn_style())
        close_btn.clicked.connect(lambda: self.window().close())
        top.addWidget(close_btn)
        root.addLayout(top)

        # ── 2x2 Mode grid — fills all available space ───────────────────
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, mode in enumerate(_MODES):
            btn = _mode_card(mode)
            btn.clicked.connect(
                lambda _c=False, r=mode["route"]: self._nav(r)
            )
            grid.addWidget(btn, i // 2, i % 2)

        root.addLayout(grid, stretch=1)

        # ── Bottom ───────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()

        back = QPushButton("\u2190  Back to Start")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setFixedSize(160, 36)
        back.setStyleSheet(f"""
            QPushButton {{
                font-size: 13px; font-weight: 600;
                background-color: transparent; color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 8px;
            }}
            QPushButton:hover {{
                color: {Color.TEXT}; border-color: {Color.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Color.SURFACE};
            }}
        """)
        back.clicked.connect(lambda: self._nav("auth"))
        bottom.addWidget(back)
        bottom.addStretch()
        root.addLayout(bottom)

    def _nav(self, page: str):
        if self._router:
            self._router.navigate(page)

    def on_enter(self, **kwargs: Any) -> None:
        pass

    def on_leave(self) -> None:
        pass
