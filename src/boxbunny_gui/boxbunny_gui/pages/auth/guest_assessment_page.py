"""Skill assessment — all 6 questions on one page, no scrolling.

Two-column grid layout to fit everything on the 1024x600 screen.
Determines suggested proficiency level from total score.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, back_link_style

logger = logging.getLogger(__name__)

_QUESTIONS = [
    ("Boxing experience?", "experience",
     ["Never", "A few times", "Regularly"]),
    ("Know the basic punches?", "punches",
     ["No", "Somewhat", "Yes"]),
    ("Can throw a 1-2-3 combo?", "combo",
     ["No", "With help", "Yes"]),
    ("Done sparring before?", "sparring",
     ["Never", "Once or twice", "Regularly"]),
    ("Your fitness level?", "fitness",
     ["Low", "Moderate", "High"]),
    ("Used boxing equipment?", "equipment",
     ["Never", "Occasionally", "Often"]),
]


def _opt_style(selected: bool) -> str:
    if selected:
        return f"""
            QPushButton {{
                font-size: 13px; font-weight: 600; padding: 8px 12px;
                min-height: 36px;
                background-color: {Color.PRIMARY}; color: {Color.BG};
                border: none; border-radius: {Size.RADIUS_SM}px;
            }}
            QPushButton:hover {{ background-color: {Color.PRIMARY_DARK}; }}
        """
    return f"""
        QPushButton {{
            font-size: 13px; font-weight: 600; padding: 8px 12px;
            min-height: 36px;
            background-color: {Color.SURFACE}; color: {Color.TEXT_SECONDARY};
            border: 1px solid {Color.BORDER}; border-radius: {Size.RADIUS_SM}px;
        }}
        QPushButton:hover {{
            border-color: {Color.PRIMARY}; color: {Color.TEXT};
            background-color: {Color.SURFACE_HOVER};
        }}
    """


class GuestAssessmentPage(QWidget):
    """Single-page skill assessment — 2-column grid, no scrolling."""

    def __init__(self, router=None, **kwargs):
        super().__init__()
        self._router = router
        self._answers: Dict[str, int] = {}
        self._btn_groups: Dict[str, list] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(50, 14, 50, 14)
        root.setSpacing(6)

        # ── Title ────────────────────────────────────────────────────────
        title = QLabel("Quick Assessment")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {Color.TEXT};"
        )
        root.addWidget(title)

        sub = QLabel("Help us tailor your training")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size: 14px; color: {Color.TEXT_SECONDARY};")
        root.addWidget(sub)

        root.addSpacing(6)

        # ── 2-column question grid ───────────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(36)
        grid.setVerticalSpacing(8)

        for idx, (prompt, key, options) in enumerate(_QUESTIONS):
            row = idx // 2
            col = idx % 2
            q_widget = self._make_question(prompt, key, options)
            grid.addWidget(q_widget, row, col)

        root.addLayout(grid, stretch=1)

        root.addSpacing(12)

        # ── Start button ─────────────────────────────────────────────────
        start_btn = QPushButton("Let's Go!")
        start_btn.setFixedSize(320, 52)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 20px; font-weight: 700;
                background-color: {Color.PRIMARY}; color: {Color.BG};
                border: none; border-radius: {Size.RADIUS}px;
            }}
            QPushButton:hover {{ background-color: {Color.PRIMARY_DARK}; }}
            QPushButton:pressed {{ background-color: {Color.PRIMARY_PRESSED}; }}
        """)
        start_btn.clicked.connect(self._on_start)
        root.addWidget(start_btn, alignment=Qt.AlignCenter)

        root.addSpacing(6)

        back = QPushButton("Back")
        back.setStyleSheet(back_link_style())
        back.clicked.connect(
            lambda: self._router.navigate("auth") if self._router else None
        )
        root.addWidget(back, alignment=Qt.AlignCenter)

    def _make_question(self, prompt: str, key: str, options: list) -> QWidget:
        """Build a question card: label + horizontal option buttons."""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {Color.SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: {Size.RADIUS}px;
            }}
        """)
        col = QVBoxLayout(container)
        col.setContentsMargins(14, 10, 14, 10)
        col.setSpacing(8)

        label = QLabel(prompt)
        label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {Color.TEXT};"
            f" background: transparent; border: none;"
        )
        label.setWordWrap(True)
        col.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(8)
        btns = []
        for idx, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setStyleSheet(_opt_style(False))
            btn.clicked.connect(
                lambda _c, k=key, i=idx, bl=btns: self._select(k, i, bl)
            )
            row.addWidget(btn)
            btns.append((idx, btn))
        col.addLayout(row)

        self._btn_groups[key] = btns
        self._select(key, 0, btns)
        return container

    def _select(self, key: str, value: int, btns: list) -> None:
        self._answers[key] = value
        for opt_idx, btn in btns:
            btn.setStyleSheet(_opt_style(opt_idx == value))

    def _compute_level(self) -> str:
        total = sum(self._answers.values())
        if total <= 4:
            return "beginner"
        if total <= 8:
            return "intermediate"
        return "advanced"

    def _on_start(self) -> None:
        level = self._compute_level()
        logger.info(
            "Assessment: %s -> level=%s (score=%d)",
            self._answers, level, sum(self._answers.values()),
        )
        if self._router:
            self._router.navigate(
                "home_guest", answers=self._answers, level=level
            )

    def on_enter(self, **kwargs: Any) -> None:
        for key, btns in self._btn_groups.items():
            self._select(key, 0, btns)

    def on_leave(self) -> None:
        pass
