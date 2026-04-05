"""Sparring setup — two-step: style selection then parameters.

Step 1: Fighting style + description (centered, clean)
Step 2: Parameters slide in, description hides, Start button appears
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import (
    Color, Icon, Size, font, PRIMARY_BTN,
    badge_style, back_link_style,
)
from boxbunny_gui.widgets import BigButton

if TYPE_CHECKING:
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)

_KW = f"color:{Color.PRIMARY}; font-weight:700"
_STYLES: Dict[str, Dict[str, str]] = {
    "Boxer": {
        "sub": "Out-fighter",
        "desc": f'<span style="{_KW}">Technical</span> style using '
                f'<span style="{_KW}">footwork</span> and '
                f'<span style="{_KW}">reach advantage</span>. '
                'Maintains distance with jabs and straights, avoiding close exchanges.',
        "range": "Long",
        "punches": "Jab / Cross",
    },
    "Brawler": {
        "sub": "Pressure",
        "desc": f'<span style="{_KW}">Aggressive</span> power puncher favouring '
                f'<span style="{_KW}">hooks</span> and '
                f'<span style="{_KW}">uppercuts</span> at close range. '
                f'<span style="{_KW}">High volume</span>, high risk, wears down opponents.',
        "range": "Close",
        "punches": "Hooks / Uppercuts",
    },
    "Counter": {
        "sub": "Exploit",
        "desc": f'<span style="{_KW}">Defensive</span> specialist. Waits for opponents '
                f'to attack, then <span style="{_KW}">counters</span> with '
                f'<span style="{_KW}">precise punches</span>. '
                f'Relies on <span style="{_KW}">timing</span> and reflexes.',
        "range": "Mid",
        "punches": "Cross / Counter",
    },
    "Pressure": {
        "sub": "Forward",
        "desc": f'<span style="{_KW}">Relentless</span> pressure fighter. '
                f'Constantly <span style="{_KW}">moves forward</span> cutting off the ring '
                f'with <span style="{_KW}">high-volume combinations</span>.',
        "range": "Close",
        "punches": "All / Body shots",
    },
    "Switch": {
        "sub": "Rhythm",
        "desc": f'<span style="{_KW}">Unpredictable</span> switch-hitter. '
                f'<span style="{_KW}">Alternates stances</span> and punch selections. '
                f'<span style="{_KW}">Hard to read</span> and prepare for.',
        "range": "Mid",
        "punches": "Mixed",
    },
}
_STYLE_ORDER = ["Boxer", "Brawler", "Counter", "Pressure", "Switch"]

_DIFFICULTIES = ["Easy", "Medium", "Hard"]
_DIFF_COLORS = {"Easy": "#3B9A6D", "Medium": "#C88D2E", "Hard": "#C0453A"}

_PARAMS: Dict[str, Dict] = {
    "Rounds":   {"opts": ["1", "2", "3", "5", "8", "12"], "accent": "#4A90D9",
                 "default": 2},
    "Duration": {"opts": ["30s", "60s", "90s", "120s", "150s", "180s"],
                 "accent": "#56B886", "default": 3},
    "Rest":     {"opts": ["30s", "60s", "90s", "120s"], "accent": "#8B7EC8",
                 "default": 1},
}


class _StyleCard(QPushButton):
    def __init__(self, name: str, sub: str, parent=None) -> None:
        super().__init__(parent)
        self.style_name = name
        self._sub = sub
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(76)
        self._update_style()

    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self._update_style()

    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Color.PRIMARY}; color: #FFFFFF;
                    border: 2px solid {Color.PRIMARY};
                    border-radius: {Size.RADIUS}px;
                    font-size: 16px; font-weight: 700; padding: 8px;
                }}
                QPushButton:hover {{ background-color: {Color.PRIMARY_DARK}; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Color.SURFACE};
                    color: {Color.TEXT_SECONDARY};
                    border: 1px solid {Color.BORDER};
                    border-radius: {Size.RADIUS}px;
                    font-size: 16px; font-weight: 600; padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: {Color.SURFACE_HOVER};
                    border-color: {Color.PRIMARY}; color: {Color.TEXT};
                }}
            """)
        self.setText(f"{self.style_name}\n{self._sub}")


class _ParamTile(QPushButton):
    def __init__(self, label: str, options: List[str], accent: str,
                 default: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._label = label
        self._options = options
        self._index: int = default
        self._accent = accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(70)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.SURFACE}; color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-left: 3px solid {self._accent};
                border-radius: {Size.RADIUS}px;
                font-size: 15px; font-weight: 600; padding: 10px 14px;
            }}
            QPushButton:hover {{
                background-color: {Color.SURFACE_HOVER};
                border-color: {self._accent};
                border-left: 3px solid {self._accent};
            }}
            QPushButton:pressed {{
                background-color: {self._accent}; color: #FFFFFF;
            }}
        """)
        self._update_text()
        self.clicked.connect(self._cycle)

    def _cycle(self) -> None:
        self._index = (self._index + 1) % len(self._options)
        self._update_text()

    def _update_text(self) -> None:
        self.setText(f"{self._label}\n{self._options[self._index]}")

    @property
    def value(self) -> str:
        return self._options[self._index]


class _DiffTile(QPushButton):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._index: int = 1
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(70)
        self.clicked.connect(self._cycle)
        self._refresh()

    def _cycle(self) -> None:
        self._index = (self._index + 1) % len(_DIFFICULTIES)
        self._refresh()

    _COUNTER_PROB = {"Easy": "30%", "Medium": "50%", "Hard": "80%"}

    def _refresh(self) -> None:
        name = _DIFFICULTIES[self._index]
        accent = _DIFF_COLORS[name]
        prob = self._COUNTER_PROB.get(name, "50%")
        self.setText(f"Difficulty\n{name} ({prob} counter)")
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.SURFACE}; color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-left: 3px solid {accent};
                border-radius: {Size.RADIUS}px;
                font-size: 15px; font-weight: 600; padding: 10px 14px;
            }}
            QPushButton:hover {{
                background-color: {Color.SURFACE_HOVER};
                border-color: {accent};
                border-left: 3px solid {accent};
            }}
            QPushButton:pressed {{
                background-color: {accent}; color: #FFFFFF;
            }}
        """)

    @property
    def value(self) -> str:
        return _DIFFICULTIES[self._index]


def _make_info_box(label: str, value: str, bg: str, border: str) -> QWidget:
    box = QWidget()
    box.setStyleSheet(f"""
        QWidget {{ background-color: {bg}; border: 1px solid {border};
            border-radius: {Size.RADIUS_SM}px; }}
        QWidget QLabel {{ background: transparent; border: none; }}
    """)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(2)
    lbl = QLabel(label.upper())
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"font-size: 10px; font-weight: 700; color: {Color.TEXT_DISABLED};"
        " letter-spacing: 1px;"
    )
    lay.addWidget(lbl)
    val = QLabel(value)
    val.setObjectName("val")
    val.setAlignment(Qt.AlignCenter)
    val.setStyleSheet(
        f"font-size: 20px; font-weight: 700; color: {Color.TEXT};"
    )
    lay.addWidget(val)
    return box


class SparringConfigPage(QWidget):
    def __init__(self, router: PageRouter, parent=None) -> None:
        super().__init__(parent)
        self._router = router
        self._selected_style: str = _STYLE_ORDER[0]
        self._style_cards: list[_StyleCard] = []
        self._tiles: Dict[str, _ParamTile] = {}
        self._step = 1  # 1 = style selection, 2 = parameters
        self._username: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 10, 32, 22)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────
        top = QHBoxLayout()
        btn_back = QPushButton(f"{Icon.BACK}  Back")
        btn_back.setStyleSheet(back_link_style())
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self._on_back)
        top.addWidget(btn_back)
        title = QLabel("Sparring Setup")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {Color.TEXT};"
        )
        top.addWidget(title)
        top.addStretch()
        mode_badge = QLabel("SPARRING")
        mode_badge.setStyleSheet(badge_style(Color.DANGER))
        top.addWidget(mode_badge)
        root.addLayout(top)

        root.addStretch(1)

        # ── Fighting Style ───────────────────────────────────────────────
        style_lbl = QLabel("Fighting Style")
        style_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {Color.TEXT_SECONDARY};"
            " letter-spacing: 0.5px;"
        )
        root.addWidget(style_lbl)
        root.addSpacing(6)

        styles_row = QHBoxLayout()
        styles_row.setSpacing(8)
        for name in _STYLE_ORDER:
            card = _StyleCard(name, _STYLES[name]["sub"], self)
            card.clicked.connect(lambda _c=False, n=name: self._pick_style(n))
            styles_row.addWidget(card)
            self._style_cards.append(card)
        root.addLayout(styles_row)
        self._refresh_style_selection()

        root.addSpacing(12)

        # ── Description + info (collapsible) ─────────────────────────────
        self._desc_section = QWidget()
        desc_outer = QVBoxLayout(self._desc_section)
        desc_outer.setContentsMargins(0, 0, 0, 0)
        desc_outer.setSpacing(10)

        desc_row = QHBoxLayout()
        desc_row.setSpacing(10)

        self._desc_text = QLabel()
        self._desc_text.setWordWrap(True)
        self._desc_text.setTextFormat(Qt.TextFormat.RichText)
        self._desc_text.setStyleSheet(f"""
            font-size: 24px; color: {Color.TEXT};
            background-color: #1A1510;
            border: 1px solid #3D2E1A;
            border-left: 3px solid {Color.PRIMARY};
            border-radius: {Size.RADIUS}px;
            padding: 28px 32px;
        """)
        desc_row.addWidget(self._desc_text, stretch=3)

        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        self._range_box = _make_info_box("Range", "", "#162030", "#2A4A6B")
        info_col.addWidget(self._range_box)
        self._punches_box = _make_info_box("Punches", "", "#1C1628", "#4A3570")
        info_col.addWidget(self._punches_box)
        desc_row.addLayout(info_col, stretch=1)

        desc_outer.addLayout(desc_row)
        root.addWidget(self._desc_section)
        self._update_description()

        # ── Parameters (hidden, appears below description) ───────────────
        self._params_section = QWidget()
        self._params_section.setMaximumHeight(0)
        params_lay = QVBoxLayout(self._params_section)
        params_lay.setContentsMargins(0, 8, 0, 0)
        params_lay.setSpacing(6)

        params_header = QHBoxLayout()
        params_lbl = QLabel("Parameters")
        params_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {Color.TEXT_SECONDARY};"
            " letter-spacing: 0.5px;"
        )
        params_header.addWidget(params_lbl)
        params_header.addStretch()
        tap_hint = QLabel("Tap to cycle")
        tap_hint.setStyleSheet(f"font-size: 11px; color: {Color.TEXT_DISABLED};")
        params_header.addWidget(tap_hint)
        params_lay.addLayout(params_header)

        params_row = QHBoxLayout()
        params_row.setSpacing(10)
        for key in ["Rounds", "Duration", "Rest"]:
            p = _PARAMS[key]
            tile = _ParamTile(key, p["opts"], p["accent"], p.get("default", 0), self)
            params_row.addWidget(tile)
            self._tiles[key] = tile
        self._diff_tile = _DiffTile(self)
        params_row.addWidget(self._diff_tile)
        params_lay.addLayout(params_row)

        params_lay.addSpacing(10)

        # Dynamic counters toggle (robot counter-punches when user hits pads)
        counter_box = QWidget()
        counter_box.setStyleSheet(f"""
            QWidget {{
                background-color: {Color.SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: {Size.RADIUS}px;
            }}
        """)
        counter_box_lay = QVBoxLayout(counter_box)
        counter_box_lay.setContentsMargins(14, 10, 14, 14)
        counter_box_lay.setSpacing(8)

        counter_row = QHBoxLayout()
        counter_row.setSpacing(8)
        counter_lbl = QLabel("Dynamic Counters")
        counter_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {Color.TEXT};"
            " background: transparent; border: none;")
        counter_row.addWidget(counter_lbl)
        counter_row.addStretch()
        self._counters_cb = QCheckBox("ON")
        self._counters_cb.setChecked(True)
        self._counters_cb.setFont(font(Size.TEXT_BODY))
        self._counters_cb.setStyleSheet(
            f"color: {Color.TEXT_SECONDARY}; background: transparent; border: none;")
        self._counters_cb.toggled.connect(self._on_counter_toggle)
        counter_row.addWidget(self._counters_cb)
        counter_box_lay.addLayout(counter_row)

        # Counter speed selector (slides in when counters ON)
        # Uses a tap-to-cycle button: Slow → Medium → Fast → Custom
        # At Custom, a slider slides out beside it
        self._counter_speed_section = QWidget()
        self._counter_speed_section.setMaximumHeight(60)
        self._counter_speed_section.setStyleSheet("background: transparent; border: none;")
        cs_lay = QHBoxLayout(self._counter_speed_section)
        cs_lay.setContentsMargins(0, 6, 0, 0)
        cs_lay.setSpacing(6)

        _SPEED_ACCENT = "#C88D2E"
        self._cs_options = ["Slow", "Medium", "Fast", "Custom"]
        self._cs_idx = 1  # Medium
        self._cs_custom_rads: float = 15.0
        self._counter_speed = "medium"

        self._cs_btn = QPushButton("Counter Speed: Medium")
        self._cs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cs_btn.setFixedHeight(50)
        self._cs_btn.setMinimumWidth(200)
        self._cs_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Color.BG}; color: {Color.TEXT};
                font-size: 13px; font-weight: 600;
                border: 1px solid {Color.BORDER};
                border-left: 3px solid {_SPEED_ACCENT};
                border-radius: 6px; padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: {Color.SURFACE_HOVER};
                border-color: {_SPEED_ACCENT};
                border-left: 3px solid {_SPEED_ACCENT};
            }}
            QPushButton:pressed {{ background: {_SPEED_ACCENT}; color: #fff; }}
        """)
        self._cs_btn.clicked.connect(self._cycle_counter_speed)
        cs_lay.addWidget(self._cs_btn)

        # Slider (hidden, slides in at Custom)
        from PySide6.QtWidgets import QSlider
        self._cs_slider_w = QWidget()
        self._cs_slider_w.setMaximumWidth(0)
        self._cs_slider_w.setStyleSheet("background: transparent; border: none;")
        sl_lay = QHBoxLayout(self._cs_slider_w)
        sl_lay.setContentsMargins(0, 0, 0, 0)
        sl_lay.setSpacing(4)
        self._cs_val_lbl = QLabel("15")
        self._cs_val_lbl.setFixedWidth(28)
        self._cs_val_lbl.setAlignment(Qt.AlignCenter)
        self._cs_val_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {_SPEED_ACCENT};"
            " background: transparent; border: none;")
        sl_lay.addWidget(self._cs_val_lbl)
        self._cs_slider = QSlider(Qt.Horizontal)
        self._cs_slider.setRange(1, 30)
        self._cs_slider.setValue(15)
        self._cs_slider.setMinimumWidth(100)
        self._cs_slider.setMinimumHeight(30)
        self._cs_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {Color.BG}; height: 8px; border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {_SPEED_ACCENT}; width: 22px; height: 22px;
                margin: -8px 0; border-radius: 11px;
                border: 2px solid {Color.SURFACE};
            }}
            QSlider::sub-page:horizontal {{
                background: {_SPEED_ACCENT}; border-radius: 4px;
            }}
        """)
        self._cs_slider.valueChanged.connect(self._on_cs_slide)
        sl_lay.addWidget(self._cs_slider)
        cs_lay.addWidget(self._cs_slider_w)

        counter_box_lay.addWidget(self._counter_speed_section)
        params_lay.addWidget(counter_box)

        root.addWidget(self._params_section)

        # Animations
        self._desc_anim = QPropertyAnimation(self._desc_section, b"maximumHeight")
        self._desc_anim.setDuration(300)
        self._desc_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._params_anim = QPropertyAnimation(self._params_section, b"maximumHeight")
        self._params_anim.setDuration(300)
        self._params_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._cs_anim = QPropertyAnimation(self._counter_speed_section, b"maximumHeight")
        self._cs_anim.setDuration(250)
        self._cs_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._cs_sl_anim = QPropertyAnimation(self._cs_slider_w, b"maximumWidth")
        self._cs_sl_anim.setDuration(250)
        self._cs_sl_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        root.addStretch(2)

        # ── Action button ────────────────────────────────────────────────
        self._btn_action = BigButton(
            f"{Icon.PLAY}  Choose Parameters", stylesheet=PRIMARY_BTN
        )
        self._btn_action.setFixedHeight(70)
        self._btn_action.clicked.connect(self._on_action)
        root.addWidget(self._btn_action)

    def _pick_style(self, name: str) -> None:
        self._selected_style = name
        self._refresh_style_selection()
        self._update_description()
        # If on step 2, go back to step 1
        if self._step == 2:
            self._show_step1()

    def _refresh_style_selection(self) -> None:
        for card in self._style_cards:
            card.set_selected(card.style_name == self._selected_style)

    def _update_description(self) -> None:
        info = _STYLES[self._selected_style]
        self._desc_text.setText(
            f'<span style="color:{Color.TEXT}; font-size:15px;">'
            f'{info["desc"]}</span>'
        )
        self._range_box.findChild(QLabel, "val").setText(info["range"])
        self._punches_box.findChild(QLabel, "val").setText(info["punches"])

    def _show_step1(self) -> None:
        """Show description, hide parameters."""
        self._step = 1
        self._btn_action.setText(f"{Icon.PLAY}  Choose Parameters")

        # Expand description
        self._desc_anim.stop()
        self._desc_anim.setStartValue(self._desc_section.maximumHeight())
        self._desc_anim.setEndValue(200)
        self._desc_anim.start()

        # Collapse parameters
        self._params_anim.stop()
        self._params_anim.setStartValue(self._params_section.height())
        self._params_anim.setEndValue(0)
        self._params_anim.start()

    def _show_step2(self) -> None:
        """Hide description, show parameters."""
        self._step = 2
        self._btn_action.setText(f"{Icon.PLAY}  Start Sparring")

        # Collapse description
        self._desc_anim.stop()
        self._desc_anim.setStartValue(self._desc_section.height())
        self._desc_anim.setEndValue(0)
        self._desc_anim.start()

        # Expand parameters
        self._params_anim.stop()
        self._params_anim.setStartValue(0)
        self._params_anim.setEndValue(250)
        self._params_anim.start()

    def imu_start(self) -> None:
        """Called by centre pad IMU."""
        self._on_action()

    def _on_action(self) -> None:
        if self._step == 1:
            self._show_step2()
        else:
            self._on_start()

    def _on_back(self) -> None:
        if self._step == 2:
            self._show_step1()
        else:
            self._router.back()

    def _on_counter_toggle(self, checked: bool) -> None:
        """Slide the counter speed section in/out."""
        self._cs_anim.stop()
        self._cs_anim.setStartValue(self._counter_speed_section.maximumHeight())
        self._cs_anim.setEndValue(60 if checked else 0)
        self._cs_anim.start()
        if not checked:
            self._cs_sl_anim.stop()
            self._cs_sl_anim.setStartValue(self._cs_slider_w.maximumWidth())
            self._cs_sl_anim.setEndValue(0)
            self._cs_sl_anim.start()

    def _cycle_counter_speed(self) -> None:
        """Cycle Slow → Medium → Fast → Custom."""
        _SPEED_ACCENT = "#C88D2E"
        self._cs_idx = (self._cs_idx + 1) % len(self._cs_options)
        name = self._cs_options[self._cs_idx]
        _normal = f"""
            QPushButton {{
                background: {Color.BG}; color: {Color.TEXT};
                font-size: 13px; font-weight: 600;
                border: 1px solid {Color.BORDER};
                border-left: 3px solid {_SPEED_ACCENT};
                border-radius: 6px; padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: {Color.SURFACE_HOVER};
                border-color: {_SPEED_ACCENT};
                border-left: 3px solid {_SPEED_ACCENT};
            }}
            QPushButton:pressed {{ background: {_SPEED_ACCENT}; color: #fff; }}
        """
        _custom = f"""
            QPushButton {{
                background: {Color.BG}; color: {Color.TEXT};
                font-size: 13px; font-weight: 600;
                border: 2px solid {_SPEED_ACCENT};
                border-radius: 6px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: {Color.SURFACE_HOVER}; }}
            QPushButton:pressed {{ background: {_SPEED_ACCENT}; color: #fff; }}
        """
        if name == "Custom":
            self._counter_speed = str(self._cs_custom_rads)
            self._cs_btn.setText(f"Counter Speed: {int(self._cs_custom_rads)} rad/s")
            self._cs_btn.setStyleSheet(_custom)
        else:
            self._counter_speed = {"Slow": "slow", "Medium": "medium", "Fast": "fast"}[name]
            self._cs_btn.setText(f"Counter Speed: {name}")
            self._cs_btn.setStyleSheet(_normal)
        cur = self._cs_slider_w.width()
        self._cs_sl_anim.stop()
        if name == "Custom":
            self._cs_sl_anim.setStartValue(cur)
            self._cs_sl_anim.setEndValue(16777215)
        else:
            self._cs_slider_w.setMaximumWidth(cur)
            self._cs_sl_anim.setStartValue(cur)
            self._cs_sl_anim.setEndValue(0)
        self._cs_sl_anim.start()

    def _on_cs_slide(self, val: int) -> None:
        self._cs_val_lbl.setText(str(val))
        self._cs_custom_rads = float(val)
        self._counter_speed = str(float(val))
        self._cs_btn.setText(f"Counter Speed: {val} rad/s")

    def _on_start(self) -> None:
        config = {k: t.value for k, t in self._tiles.items()}
        config["style"] = self._selected_style
        config["difficulty"] = self._diff_tile.value
        config["counters_enabled"] = self._counters_cb.isChecked()
        config["counter_speed"] = self._counter_speed if self._counters_cb.isChecked() else "medium"
        logger.info("Starting sparring: %s", config)
        self._router.navigate(
            "sparring_session", config=config, username=self._username,
        )

    def _save_as_preset(self) -> None:
        """Save sparring config as a preset."""
        if not self._username:
            return
        import json, sqlite3
        from pathlib import Path
        config = {k: t.value for k, t in self._tiles.items()}
        cfg_json = json.dumps({
            "rounds": int(config.get("Rounds", "3")),
            "work_sec": int(config.get("Duration", "90s").rstrip("s")),
            "rest_sec": int(config.get("Rest", "60s").rstrip("s")),
            "speed": "medium",
            "difficulty": self._diff_tile.value,
            "style": self._selected_style,
            "route": "sparring_session",
        })
        try:
            db_path = Path("/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws/data/boxbunny_main.db")
            conn = sqlite3.connect(str(db_path))
            user_row = conn.execute("SELECT id FROM users WHERE username = ?", (self._username,)).fetchone()
            if user_row:
                conn.execute(
                    "INSERT INTO presets (user_id, name, description, preset_type, config_json) VALUES (?, ?, ?, 'sparring', ?)",
                    (user_row[0], f"Sparring: {self._selected_style}", f"{self._diff_tile.value} {self._selected_style}", cfg_json),
                )
                conn.commit()
                logger.info("Sparring preset saved for %s", self._username)
            conn.close()
        except Exception as exc:
            logger.warning("Failed to save preset: %s", exc)

    def on_enter(self, **kwargs: Any) -> None:
        self._username = kwargs.get("username", "")
        self._step = 1
        self._desc_section.setMaximumHeight(200)
        self._params_section.setMaximumHeight(0)
        self._btn_action.setText(f"{Icon.PLAY}  Choose Parameters")
        logger.debug("SparringConfigPage entered")

    def on_leave(self) -> None:
        pass
