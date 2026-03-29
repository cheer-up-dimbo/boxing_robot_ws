"""Full-screen sparring session page.

Timer, round counter, robot attack indicator, live offense/defense
stats, and stop button. Connects to gui_bridge signals.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, DANGER_BTN, badge_style, button_style
from boxbunny_gui.widgets import BigButton, PunchCounter, TimerDisplay

if TYPE_CHECKING:
    from boxbunny_gui.gui_bridge import GuiBridge
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)


def _stat_column(label: str, value: str, color: str) -> tuple:
    """Create a labeled stat column inside a surface card, returning (frame, value_label)."""
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background-color: {Color.SURFACE};"
        f" border-radius: 14px;"
        f" border-top: 2px solid {color}; }}"
    )
    frame.setMinimumWidth(120)
    col = QVBoxLayout(frame)
    col.setAlignment(Qt.AlignmentFlag.AlignCenter)
    col.setContentsMargins(12, 10, 12, 10)
    col.setSpacing(2)

    h_label = QLabel(label)
    h_label.setStyleSheet(
        f"color: {Color.TEXT_DISABLED}; font-size: 11px;"
        " font-weight: 700; letter-spacing: 0.8px;"
    )
    h_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    v_label = QLabel(value)
    v_label.setFont(font(32, bold=True))
    v_label.setStyleSheet(f"color: {color};")
    v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    col.addWidget(h_label)
    col.addWidget(v_label)
    return frame, v_label


class SparringSessionPage(QWidget):
    """Live sparring session with offense/defense tracking."""

    def __init__(
        self,
        router: PageRouter,
        bridge: Optional[GuiBridge] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._router = router
        self._bridge = bridge
        self._config: Dict[str, Any] = {}
        self._hits_taken: int = 0
        self._total_attacks: int = 0
        self._build_ui()
        self._connect_bridge()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            Size.SPACING, Size.SPACING_SM, Size.SPACING, Size.SPACING_SM
        )
        root.setSpacing(Size.SPACING_SM)

        # Top: round counter + mode badge
        top = QHBoxLayout()
        self._round_lbl = QLabel("Round 1/3")
        self._round_lbl.setFont(font(20, bold=True))
        self._round_lbl.setStyleSheet(f"color: {Color.TEXT};")
        top.addWidget(self._round_lbl)
        top.addStretch()

        mode_lbl = QLabel("SPARRING")
        mode_lbl.setStyleSheet(badge_style(Color.DANGER))
        top.addWidget(mode_lbl)
        root.addLayout(top)

        # Timer
        self._timer = TimerDisplay(font_size=Size.TEXT_TIMER_SM, show_ring=True)
        self._timer.finished.connect(self._on_timer_done)
        root.addWidget(self._timer, stretch=1)

        # Robot attack indicator
        attack_frame = QFrame()
        attack_frame.setFixedHeight(64)
        attack_frame.setStyleSheet(
            f"QFrame {{ background-color: {Color.SURFACE};"
            f" border: 1px solid {Color.BORDER};"
            f" border-left: 4px solid {Color.WARNING};"
            f" border-radius: 14px; }}"
        )
        attack_lay = QHBoxLayout(attack_frame)
        attack_lay.setContentsMargins(16, 0, 16, 0)
        attack_tag = QLabel("INCOMING")
        attack_tag.setStyleSheet(
            f"color: {Color.TEXT_DISABLED}; font-size: 11px;"
            " font-weight: 700; letter-spacing: 1px;"
        )
        attack_lay.addWidget(attack_tag)
        self._attack_lbl = QLabel("Waiting...")
        self._attack_lbl.setFont(font(22, bold=True))
        self._attack_lbl.setStyleSheet(f"color: {Color.WARNING};")
        self._attack_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        attack_lay.addWidget(self._attack_lbl, stretch=1)
        root.addWidget(attack_frame)

        # Stats row
        stats = QHBoxLayout()
        stats.setSpacing(Size.SPACING_SM)

        self._punch_counter = PunchCounter(label="YOUR PUNCHES")
        stats.addWidget(self._punch_counter)

        hits_frame, self._hits_lbl = _stat_column(
            "HITS TAKEN", "0", Color.DANGER
        )
        stats.addWidget(hits_frame)

        def_frame, self._def_lbl = _stat_column(
            "DEFENSE RATE", "--%", Color.PRIMARY
        )
        stats.addWidget(def_frame)
        root.addLayout(stats)

        root.addSpacing(6)

        # Stop button -- centered, pill-shaped
        bottom = QHBoxLayout()
        bottom.addStretch()
        stop_style = button_style(
            Color.DANGER, Color.DANGER_DARK, "#C33C3C",
            font_size=14, min_h=44, radius=22,
        )
        self._btn_stop = BigButton("\u25A0  STOP", stylesheet=stop_style)
        self._btn_stop.setFixedWidth(140)
        self._btn_stop.clicked.connect(self._on_stop)
        bottom.addWidget(self._btn_stop)
        bottom.addStretch()
        root.addLayout(bottom)

    def _connect_bridge(self) -> None:
        if self._bridge is None:
            return
        self._bridge.punch_confirmed.connect(self._on_punch)
        self._bridge.defense_event.connect(self._on_defense)

    def _on_punch(self, data: Dict[str, Any]) -> None:
        self._punch_counter.increment()

    def _on_defense(self, data: Dict[str, Any]) -> None:
        self._total_attacks += 1
        if data.get("struck", False):
            self._hits_taken += 1
            self._hits_lbl.setText(str(self._hits_taken))
        self._attack_lbl.setText(data.get("robot_punch_code", ""))
        blocked = self._total_attacks - self._hits_taken
        rate = (
            int(100 * blocked / self._total_attacks)
            if self._total_attacks else 0
        )
        self._def_lbl.setText(f"{rate}%")

    def _on_timer_done(self) -> None:
        self._router.replace("sparring_results", config=self._config)

    def _on_stop(self) -> None:
        self._timer.pause()
        logger.info("Sparring stopped by user")
        self._router.replace("sparring_results", config=self._config)

    def _parse_seconds(self, val: str) -> int:
        return int(val.rstrip("s")) if val.rstrip("s").isdigit() else 90

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})
        rounds = self._config.get("Rounds", "3")
        work_time = self._parse_seconds(self._config.get("Work Time", "90s"))
        self._round_lbl.setText(f"Round 1/{rounds}")
        self._hits_taken = 0
        self._total_attacks = 0
        self._hits_lbl.setText("0")
        self._def_lbl.setText("--%")
        self._attack_lbl.setText("Waiting...")
        self._punch_counter.set_count(0)
        self._timer.start(work_time)
        logger.debug("SparringSessionPage entered")

    def on_leave(self) -> None:
        self._timer.pause()
