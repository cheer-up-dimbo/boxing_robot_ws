"""Guest home page — shown after skill assessment."""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from boxbunny_gui.theme import Color, Icon, Size, subtle_btn_style

logger = logging.getLogger(__name__)

_KW = f"color:{Color.PRIMARY_LIGHT}; font-weight:600"
_MODES = [
    {
        "name": "Techniques",
        "desc": f'Practice <span style="{_KW}">punch combinations</span> with '
                f'<span style="{_KW}">guided drills</span>',
        "accent": Color.PRIMARY,
        "tint": ("#1C1610", "#2E221A"),
        "route": "training_select",
    },
    {
        "name": "Sparring",
        "desc": f'<span style="{_KW}">Fight</span> against the '
                f'<span style="{_KW}">robot AI</span>',
        "accent": Color.DANGER,
        "tint": ("#1C1214", "#2E1A1E"),
        "route": "sparring_select",
    },
    {
        "name": "Free Training",
        "desc": f'<span style="{_KW}">Open session</span>, no structure',
        "accent": Color.INFO,
        "tint": ("#111820", "#1A2530"),
        "route": "training_session",
    },
    {
        "name": "Performance",
        "desc": f'Test your <span style="{_KW}">power</span>, '
                f'<span style="{_KW}">stamina</span> and '
                f'<span style="{_KW}">speed</span>',
        "accent": Color.PURPLE,
        "tint": ("#181420", "#221C30"),
        "route": "performance",
    },
]


def _mode_card(mode: dict) -> QPushButton:
    accent = mode["accent"]
    bg, border = mode.get("tint", (Color.SURFACE, Color.BORDER))
    btn = QPushButton()
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(120)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            border: 1px solid {border};
            border-left: 3px solid {accent};
            border-radius: {Size.RADIUS}px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {Color.SURFACE_HOVER};
            border: 1px solid {accent};
            border-left: 3px solid {accent};
        }}
    """)

    lay = QVBoxLayout(btn)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(8)

    title = QLabel(mode["name"])
    title.setStyleSheet(
        "background: transparent; border: none;"
        f" font-size: 24px; font-weight: 700; color: {Color.TEXT};"
    )
    title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    lay.addWidget(title)

    lay.addStretch()

    desc = QLabel(mode["desc"])
    desc.setTextFormat(Qt.TextFormat.RichText)
    desc.setStyleSheet(
        "background: transparent; border: none;"
        f" font-size: 14px; color: {Color.TEXT_SECONDARY};"
    )
    desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    lay.addWidget(desc)

    return btn


class HomeGuestPage(QWidget):
    def __init__(self, router=None, **kwargs):
        super().__init__()
        self._router = router
        self._level = "Beginner"
        self._guest_history: list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 14, 32, 22)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(10)

        self._title = QLabel("Welcome, Guest")
        self._title.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {Color.PRIMARY};"
        )
        top.addWidget(self._title)
        top.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 13px; font-weight: 600; padding: 6px 16px;
                background-color: {Color.SURFACE}; color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 8px;
            }}
            QPushButton:hover {{
                color: {Color.TEXT}; border-color: {Color.PRIMARY};
                background-color: {Color.SURFACE_LIGHT};
            }}
        """)
        settings_btn.setFixedHeight(44)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(lambda: self._nav("settings"))
        top.addWidget(settings_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 13px; font-weight: 600; padding: 6px 14px;
                background-color: {Color.SURFACE}; color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Color.DANGER}; color: white;
                border-color: {Color.DANGER};
            }}
        """)
        close_btn.setFixedHeight(44)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.window().close())
        top.addWidget(close_btn)
        root.addLayout(top)

        self._sub = QLabel("Choose a mode to get started")
        self._sub.setStyleSheet(f"font-size: 13px; color: {Color.TEXT_SECONDARY};")
        root.addWidget(self._sub)

        root.addStretch(1)

        # ── Card grid (2 cols, last row spans if odd) ────────────────────
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        for i, mode in enumerate(_MODES):
            btn = _mode_card(mode)
            btn.clicked.connect(
                lambda _c=False, r=mode["route"]: self._nav(r)
            )
            row, col = divmod(i, 2)
            # Last item spans full width if odd count
            if i == len(_MODES) - 1 and len(_MODES) % 2 == 1:
                grid.addWidget(btn, row, 0, 1, 2)
            else:
                grid.addWidget(btn, row, col)

        root.addLayout(grid)

        root.addStretch(1)

        # ── Bottom ───────────────────────────────────────────────────────
        bottom = QHBoxLayout()

        back = QPushButton(f"{Icon.BACK}  Back")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setFixedSize(120, 44)
        back.setStyleSheet(subtle_btn_style())
        back.clicked.connect(lambda: self._nav("auth"))
        bottom.addWidget(back)

        bottom.addStretch()

        history_btn = QPushButton("History")
        history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        history_btn.setFixedSize(180, 56)
        history_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px; font-weight: 700;
                background-color: transparent; color: {Color.PRIMARY_LIGHT};
                border: 1px solid {Color.PRIMARY_LIGHT}; border-radius: 10px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                color: #FFFFFF; border-color: {Color.PRIMARY};
                background-color: {Color.PRIMARY};
            }}
        """)
        history_btn.clicked.connect(lambda: self._nav("history"))
        bottom.addWidget(history_btn)

        root.addLayout(bottom)

    def _nav(self, page: str):
        if self._router:
            # Pass level and guest_history to all child pages
            self._router.navigate(
                page,
                user_level=self._level,
                guest_history=self._guest_history,
            )

    def on_enter(self, **kwargs: Any) -> None:
        level = kwargs.get("level", "")
        if level:
            # Capitalize properly: "beginner" -> "Beginner"
            level_title = level.title() if level.lower() in (
                "beginner", "intermediate", "advanced"
            ) else level
            self._level = level_title
        logger.info("HomeGuestPage entered (level=%s)", self._level)

    def on_leave(self) -> None:
        pass
