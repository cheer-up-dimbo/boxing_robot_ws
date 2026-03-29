"""Settings page: hardware, sound, display, AI, network, system sections."""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from boxbunny_gui.theme import Color, Size, font, GHOST_BTN, SURFACE_BTN
from boxbunny_gui.widgets import BigButton

if TYPE_CHECKING:
    from boxbunny_gui.gui_bridge import GuiBridge
    from boxbunny_gui.nav.router import PageRouter

logger = logging.getLogger(__name__)


class _StatusDot(QWidget):
    """Rounded status indicator with subtle glow ring."""

    def __init__(
        self, connected: bool = False, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._dot = QLabel(self)
        self._dot.setFixedSize(12, 12)
        self._dot.move(8, 8)
        self._ring = QLabel(self)
        self._ring.setFixedSize(22, 22)
        self._ring.move(3, 3)
        self.set_connected(connected)

    def set_connected(self, connected: bool) -> None:
        color = Color.PRIMARY if connected else Color.DANGER
        self._dot.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )
        self._ring.setStyleSheet(
            f"background-color: {color}20; border-radius: 11px;"
            f" border: 1px solid {color}40;"
        )


class _Section(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("section")
        self.setStyleSheet(
            f"QFrame#section {{ background-color: {Color.SURFACE};"
            f" border: 1px solid {Color.BORDER};"
            f" border-radius: 14px; }}"
        )
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 14, 20, 14)
        self._root.setSpacing(12)

        header = QLabel(title.upper())
        header.setStyleSheet(
            f"color: {Color.PRIMARY}; font-size: 12px; font-weight: 700;"
            " letter-spacing: 1px;"
        )
        self._root.addWidget(header)

        # Thin divider line
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Color.BORDER};")
        self._root.addWidget(divider)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 2, 0, 2)
        self._content_lay.setSpacing(10)
        self._root.addWidget(self._content)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_lay


def _setting_row(label_text: str) -> tuple:
    """Create a standard settings row with label and return (layout, label)."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 4, 0, 4)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"font-size: 14px; color: {Color.TEXT};")
    row.addWidget(lbl)
    row.addStretch()
    return row, lbl


class SettingsPage(QWidget):
    def __init__(
        self,
        router: PageRouter,
        bridge: Optional[GuiBridge] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._router = router
        self._bridge = bridge
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            Size.SPACING_LG, Size.SPACING, Size.SPACING_LG, Size.SPACING_SM
        )
        root.setSpacing(Size.SPACING)

        # Top bar
        top = QHBoxLayout()
        btn_back = BigButton("Back", stylesheet=GHOST_BTN)
        btn_back.setFixedWidth(100)
        btn_back.clicked.connect(lambda: self._router.back())
        top.addWidget(btn_back)
        title = QLabel("Settings")
        title.setFont(font(Size.TEXT_SUBHEADER, bold=True))
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # Scrollable sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        sections = QVBoxLayout(container)
        sections.setSpacing(14)
        sections.setContentsMargins(2, 4, 2, 4)

        # Hardware
        hw = _Section("Hardware")
        for device in ["Camera", "Robot", "IMU Left", "IMU Right"]:
            row, _ = _setting_row(device)
            dot = _StatusDot(connected=False)
            row.addWidget(dot)
            hw.content_layout.addLayout(row)
        sections.addWidget(hw)

        # Sound
        snd = _Section("Sound")
        vol_row, _ = _setting_row("Master Volume")
        self._vol_label = QLabel("80%")
        self._vol_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {Color.PRIMARY};"
            f" background-color: {Color.PRIMARY_MUTED}; border-radius: 8px;"
            " padding: 2px 10px;"
        )
        self._vol_label.setFixedWidth(48)
        self._vol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_row.addWidget(self._vol_label)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(80)
        slider.setMinimumHeight(44)
        slider.setMinimumWidth(180)
        slider.valueChanged.connect(
            lambda v: self._vol_label.setText(f"{v}%")
        )
        vol_row.addWidget(slider)
        snd.content_layout.addLayout(vol_row)
        for toggle_name in ["Punch Sounds", "Timer Beeps", "Coach Voice"]:
            row, _ = _setting_row(toggle_name)
            cb = QCheckBox()
            cb.setChecked(True)
            row.addWidget(cb)
            snd.content_layout.addLayout(row)
        sections.addWidget(snd)

        # Display
        disp = _Section("Display")
        row, _ = _setting_row("Gesture Control")
        cb = QCheckBox()
        row.addWidget(cb)
        disp.content_layout.addLayout(row)
        sections.addWidget(disp)

        # AI Coach
        ai = _Section("AI Coach")
        row, _ = _setting_row("Enable AI Coach")
        self._ai_cb = QCheckBox()
        self._ai_cb.setChecked(True)
        row.addWidget(self._ai_cb)
        ai.content_layout.addLayout(row)
        row2, _ = _setting_row("LLM Status")
        self._llm_dot = _StatusDot(connected=False)
        row2.addWidget(self._llm_dot)
        ai.content_layout.addLayout(row2)
        sections.addWidget(ai)

        # Network
        net = _Section("Network")
        net_row, _ = _setting_row("WiFi AP Status")
        self._wifi_dot = _StatusDot(connected=True)
        net_row.addWidget(self._wifi_dot)
        net.content_layout.addLayout(net_row)

        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_icon = QLabel("\U0001F310")
        url_icon.setStyleSheet("font-size: 13px;")
        url_row.addWidget(url_icon)
        url_lbl = QLabel("boxbunny.local")
        url_lbl.setStyleSheet(
            f"color: {Color.TEXT_SECONDARY}; font-size: 13px;"
            f" background-color: {Color.SURFACE_LIGHT}; border-radius: 8px;"
            " padding: 4px 12px;"
        )
        url_row.addWidget(url_lbl)
        url_row.addStretch()
        net.content_layout.addLayout(url_row)
        sections.addWidget(net)

        # System
        sys_sec = _Section("System")

        info_row = QHBoxLayout()
        info_row.setSpacing(12)
        ver = QLabel("BoxBunny v1.0.0")
        ver.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {Color.TEXT_SECONDARY};"
            f" background-color: {Color.SURFACE_LIGHT}; border-radius: 8px;"
            " padding: 5px 14px;"
        )
        info_row.addWidget(ver)
        db_lbl = QLabel("DB: sessions.db")
        db_lbl.setStyleSheet(
            f"font-size: 13px; color: {Color.TEXT_DISABLED};"
            f" background-color: {Color.SURFACE_LIGHT}; border-radius: 8px;"
            " padding: 5px 14px;"
        )
        info_row.addWidget(db_lbl)
        info_row.addStretch()
        sys_sec.content_layout.addLayout(info_row)

        btn_maint = BigButton("Database Maintenance", stylesheet=SURFACE_BTN)
        btn_maint.setFixedHeight(44)
        sys_sec.content_layout.addWidget(btn_maint)
        sections.addWidget(sys_sec)

        sections.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

    def on_enter(self, **kwargs: Any) -> None:
        logger.debug("SettingsPage entered")

    def on_leave(self) -> None:
        pass
