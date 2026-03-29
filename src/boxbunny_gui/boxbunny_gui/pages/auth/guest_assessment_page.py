"""Quick skill assessment for guest users (3 questions, one at a time).

Collects experience level, goal, and preferred intensity.
Progress dots at top indicate current question.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, PRIMARY_BTN, SURFACE_BTN
from boxbunny_gui.widgets import BigButton

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_QUESTIONS: List[Dict[str, Any]] = [
    {
        "prompt": "Have you boxed before?",
        "key": "experience",
        "options": ["Yes", "No"],
    },
    {
        "prompt": "What's your goal?",
        "key": "goal",
        "options": ["Fitness", "Learn Boxing", "Improve Skills"],
    },
    {
        "prompt": "Preferred intensity?",
        "key": "intensity",
        "options": ["Light", "Medium", "Hard"],
    },
]


class GuestAssessmentPage(QWidget):
    """Three-question wizard that feeds into the guest home page."""

    def __init__(self, router: PageRouter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._step: int = 0
        self._answers: Dict[str, str] = {}
        self._option_btns: list[BigButton] = []
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(Size.SPACING_LG, Size.SPACING_LG,
                                      Size.SPACING_LG, Size.SPACING_LG)
        self._root.setSpacing(Size.SPACING)

        # Progress dots
        self._dots_layout = QHBoxLayout()
        self._dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dots: list[QLabel] = []
        for i in range(len(_QUESTIONS)):
            dot = QLabel()
            dot.setFixedSize(14, 14)
            self._dots.append(dot)
            self._dots_layout.addWidget(dot)
        self._root.addLayout(self._dots_layout)

        # Prompt label
        self._prompt = QLabel()
        self._prompt.setFont(font(Size.TEXT_HEADER, bold=True))
        self._prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prompt.setWordWrap(True)
        self._root.addStretch(1)
        self._root.addWidget(self._prompt)
        self._root.addStretch(1)

        # Option buttons container
        self._btn_layout = QVBoxLayout()
        self._btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_layout.setSpacing(Size.SPACING)
        self._root.addLayout(self._btn_layout)
        self._root.addStretch(2)

    def _refresh_step(self) -> None:
        """Rebuild widgets for the current question step."""
        # Clear old buttons
        for btn in self._option_btns:
            self._btn_layout.removeWidget(btn)
            btn.deleteLater()
        self._option_btns.clear()

        q = _QUESTIONS[self._step]
        self._prompt.setText(q["prompt"])

        # Update dots
        for i, dot in enumerate(self._dots):
            active = i == self._step
            dot.setStyleSheet(
                f"background-color: {Color.PRIMARY if active else Color.SURFACE_LIGHT};"
                f" border-radius: 7px;"
            )

        # Create option buttons
        for opt in q["options"]:
            btn = BigButton(opt, stylesheet=SURFACE_BTN)
            btn.setFixedWidth(int(Size.SCREEN_W * 0.55))
            btn.clicked.connect(lambda _checked=False, o=opt: self._pick(o))
            self._btn_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self._option_btns.append(btn)

    def _pick(self, value: str) -> None:
        q = _QUESTIONS[self._step]
        self._answers[q["key"]] = value
        self._step += 1
        if self._step >= len(_QUESTIONS):
            logger.info("Guest assessment complete: %s", self._answers)
            self._router.navigate("home_guest", **self._answers)
        else:
            self._refresh_step()

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._step = 0
        self._answers.clear()
        self._refresh_step()
        logger.debug("GuestAssessmentPage entered")

    def on_leave(self) -> None:
        pass
