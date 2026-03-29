"""Full-screen active training session page.

Timer, combo display with highlighting, round counter, live punch counter,
coach tip bar, and stop button. Connects to gui_bridge signals.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, DANGER_BTN
from boxbunny_gui.widgets import BigButton, CoachTipBar, ComboDisplay, PunchCounter, TimerDisplay

if TYPE_CHECKING:
    from boxbunny_gui.gui_bridge import GuiBridge
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)


class TrainingSessionPage(QWidget):
    """Active training session with live ROS data display."""

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
        self._current_round: int = 1
        self._total_rounds: int = 3
        self._build_ui()
        self._connect_bridge()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Size.SPACING, Size.SPACING_SM, Size.SPACING, Size.SPACING_SM)
        root.setSpacing(Size.SPACING_SM)

        # Coach tip bar (collapsible, top)
        self._coach_bar = CoachTipBar(parent=self)
        root.addWidget(self._coach_bar)

        # Top row: timer + round counter
        top_row = QHBoxLayout()
        self._timer = TimerDisplay(font_size=Size.TEXT_TIMER, show_ring=True)
        self._timer.finished.connect(self._on_timer_done)
        top_row.addWidget(self._timer, stretch=1)

        self._round_lbl = QLabel("Round 1/3")
        self._round_lbl.setFont(font(22, bold=True))
        self._round_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(self._round_lbl)
        root.addLayout(top_row)

        # Combo display (center)
        self._combo_display = ComboDisplay(parent=self)
        root.addWidget(self._combo_display, stretch=1)

        # Bottom row: punch counter (left) + stop button (right)
        bottom = QHBoxLayout()
        self._punch_counter = PunchCounter(label="PUNCHES")
        bottom.addWidget(self._punch_counter)
        bottom.addStretch()

        self._btn_stop = BigButton("STOP", stylesheet=DANGER_BTN)
        self._btn_stop.setFixedSize(80, 80)
        self._btn_stop.clicked.connect(self._on_stop)
        bottom.addWidget(self._btn_stop, alignment=Qt.AlignmentFlag.AlignBottom)
        root.addLayout(bottom)

    def _connect_bridge(self) -> None:
        if self._bridge is None:
            return
        self._bridge.punch_confirmed.connect(self._on_punch)
        self._bridge.drill_progress.connect(self._on_drill_progress)
        self._bridge.coach_tip.connect(self._on_coach_tip)
        self._bridge.session_state_changed.connect(self._on_session_state)

    def _on_punch(self, data: Dict[str, Any]) -> None:
        self._punch_counter.increment()

    def _on_drill_progress(self, data: Dict[str, Any]) -> None:
        # TODO: update combo display highlighting from progress data
        pass

    def _on_coach_tip(self, text: str, tip_type: str) -> None:
        self._coach_bar.show_tip(text, tip_type)

    def _on_session_state(self, state: str, mode: str) -> None:
        if state == "rest":
            self._router.replace("training_rest", config=self._config,
                                 round_num=self._current_round,
                                 total_rounds=self._total_rounds)

    def _on_timer_done(self) -> None:
        if self._current_round < self._total_rounds:
            self._router.replace("training_rest", config=self._config,
                                 round_num=self._current_round,
                                 total_rounds=self._total_rounds)
        else:
            self._router.replace("training_results", config=self._config)

    def _on_stop(self) -> None:
        self._timer.pause()
        logger.info("Training session stopped by user")
        self._router.replace("training_results", config=self._config)

    def _parse_seconds(self, val: str) -> int:
        return int(val.rstrip("s")) if val.rstrip("s").isdigit() else 90

    # ── Lifecycle ──────────────────────────────────────────────────────
    def on_enter(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})
        self._total_rounds = int(self._config.get("Rounds", "3"))
        self._current_round = kwargs.get("round_num", 1)
        work_time = self._parse_seconds(self._config.get("Work Time", "90s"))
        self._round_lbl.setText(f"Round {self._current_round}/{self._total_rounds}")
        self._punch_counter.set_count(0)
        self._timer.start(work_time)
        logger.debug("TrainingSessionPage entered (round %d/%d)",
                      self._current_round, self._total_rounds)

    def on_leave(self) -> None:
        self._timer.pause()
