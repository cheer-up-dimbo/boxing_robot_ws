"""Pattern lock screen for user authentication.

Shows selected user's name and a 3x3 grid of buttons as a placeholder
for a full pattern-lock widget.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, GHOST_BTN, SURFACE_BTN
from boxbunny_gui.widgets import BigButton

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_CORRECT_PATTERN = [0, 1, 2, 5, 8]  # placeholder -- top row then down-right


class PatternLockPage(QWidget):
    """3x3 pattern lock with QR fallback."""

    def __init__(self, router: PageRouter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._router = router
        self._user_id: str = ""
        self._user_name: str = ""
        self._entered: List[int] = []
        self._cells: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Size.SPACING_LG, Size.SPACING_LG,
                                Size.SPACING_LG, Size.SPACING_LG)
        root.setSpacing(Size.SPACING)

        # User name
        self._name_lbl = QLabel()
        self._name_lbl.setFont(font(Size.TEXT_SUBHEADER, bold=True))
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._name_lbl)

        self._status_lbl = QLabel("Enter your pattern")
        self._status_lbl.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; font-size: 16px;")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._status_lbl)

        root.addStretch(1)

        # 3x3 grid
        grid_container = QWidget()
        grid_container.setFixedSize(240, 240)
        grid = QGridLayout(grid_container)
        grid.setSpacing(Size.SPACING)
        for i in range(9):
            btn = QPushButton()
            btn.setFixedSize(60, 60)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {Color.SURFACE_LIGHT};"
                f" border-radius: 30px; border: 2px solid {Color.BORDER}; }}"
                f" QPushButton:hover {{ background-color: {Color.SURFACE_HOVER}; }}"
            )
            btn.clicked.connect(lambda _ch=False, idx=i: self._tap_cell(idx))
            grid.addWidget(btn, i // 3, i % 3)
            self._cells.append(btn)

        root.addWidget(grid_container, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(1)

        # Bottom row
        bottom = QHBoxLayout()
        self._btn_back = BigButton("Back", stylesheet=GHOST_BTN)
        self._btn_back.setFixedWidth(100)
        self._btn_back.clicked.connect(lambda: self._router.back())
        bottom.addWidget(self._btn_back)
        bottom.addStretch()
        self._btn_qr = BigButton("Use QR instead", stylesheet=SURFACE_BTN)
        self._btn_qr.setFixedWidth(200)
        self._btn_qr.clicked.connect(self._on_qr_fallback)
        bottom.addWidget(self._btn_qr)
        root.addLayout(bottom)

    def _tap_cell(self, idx: int) -> None:
        if idx in self._entered:
            return
        self._entered.append(idx)
        self._cells[idx].setStyleSheet(
            f"QPushButton {{ background-color: {Color.PRIMARY};"
            f" border-radius: 30px; border: 2px solid {Color.PRIMARY_DARK}; }}"
        )
        if len(self._entered) >= 5:
            self._check_pattern()

    def _check_pattern(self) -> None:
        if self._entered == _CORRECT_PATTERN:
            logger.info("Pattern correct for user %s", self._user_id)
            self._router.navigate("home_individual", user_id=self._user_id)
        else:
            logger.info("Incorrect pattern attempt for user %s", self._user_id)
            self._status_lbl.setText("Incorrect pattern -- try again")
            self._status_lbl.setStyleSheet(f"color: {Color.DANGER}; font-size: 16px;")
            self._reset_grid()

    def _reset_grid(self) -> None:
        self._entered.clear()
        for btn in self._cells:
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {Color.SURFACE_LIGHT};"
                f" border-radius: 30px; border: 2px solid {Color.BORDER}; }}"
                f" QPushButton:hover {{ background-color: {Color.SURFACE_HOVER}; }}"
            )

    def _on_qr_fallback(self) -> None:
        # TODO: open QR scanner overlay
        logger.info("QR fallback requested")

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._user_id = kwargs.get("user_id", "")
        self._user_name = kwargs.get("user_name", "User")
        self._name_lbl.setText(self._user_name)
        self._status_lbl.setText("Enter your pattern")
        self._status_lbl.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; font-size: 16px;")
        self._reset_grid()
        logger.debug("PatternLockPage entered for user %s", self._user_id)

    def on_leave(self) -> None:
        self._reset_grid()
