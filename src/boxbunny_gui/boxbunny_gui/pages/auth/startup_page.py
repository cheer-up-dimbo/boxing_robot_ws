"""Startup page — first screen users see.

Clean, modern dark UI. Large buttons, clear hierarchy, no clutter.
QR popup for phone dashboard access via a small button in the corner.
"""
from __future__ import annotations

import logging
import socket
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from boxbunny_gui.theme import Color, Size, close_btn_style

logger = logging.getLogger(__name__)


class _QrPopup(QDialog):
    """Full-screen QR code popup for phone dashboard scanning."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan QR Code")
        self.setFixedSize(500, 500)
        self.setStyleSheet(f"background-color: {Color.BG};")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)

        title = QLabel("Scan with your phone")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {Color.TEXT};"
        )
        layout.addWidget(title)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "localhost"

        url = f"http://{ip}:8080"

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setFixedSize(300, 300)
        try:
            import qrcode
            from io import BytesIO
            from PySide6.QtGui import QPixmap

            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="white", back_color=Color.BG)
            buf = BytesIO()
            img.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())
            qr_label.setPixmap(
                pix.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        except ImportError:
            qr_label.setText("QR code library not installed\npip install qrcode pillow")
            qr_label.setStyleSheet(f"color: {Color.DANGER}; font-size: 14px;")
        layout.addWidget(qr_label, alignment=Qt.AlignCenter)

        url_label = QLabel(url)
        url_label.setAlignment(Qt.AlignCenter)
        url_label.setStyleSheet(
            f"font-size: 16px; color: {Color.PRIMARY}; font-weight: 600;"
        )
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(url_label)

        hint = QLabel("Scan the QR code or visit the URL to log in")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"font-size: 14px; color: {Color.TEXT_SECONDARY};")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        close_btn = QPushButton("Close")
        close_btn.setFixedSize(140, 44)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 16px; font-weight: 600;
                background-color: {Color.SURFACE}; color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 10px;
            }}
            QPushButton:hover {{ color: {Color.TEXT}; border-color: {Color.PRIMARY}; }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)


class StartupPage(QWidget):
    """Landing screen — branding + clear entry points."""

    def __init__(self, router=None, **kwargs):
        super().__init__()
        self._router = router

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(80, 24, 80, 24)

        # ── Close button (top-right) ─────────────────────────────────────
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(38, 38)
        close_btn.setStyleSheet(close_btn_style())
        close_btn.clicked.connect(lambda: self.window().close())

        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(close_btn)
        root.addLayout(top)

        root.addStretch(4)

        # ── Branding ─────────────────────────────────────────────────────
        title = QLabel("BoxBunny")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 54px; font-weight: 800; color: {Color.PRIMARY};"
            " letter-spacing: 2px;"
        )

        subtitle = QLabel("AI Boxing Training Robot")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 17px; color: {Color.TEXT_SECONDARY};"
            " letter-spacing: 3px; text-transform: uppercase;"
        )

        root.addWidget(title, alignment=Qt.AlignCenter)
        root.addSpacing(6)
        root.addWidget(subtitle, alignment=Qt.AlignCenter)

        root.addStretch(3)

        # ── Primary action — clearly labeled as guest ────────────────────
        start_btn = QPushButton("Quick Start (Guest)")
        start_btn.setFixedSize(480, 64)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 22px; font-weight: 700;
                background-color: {Color.PRIMARY}; color: {Color.BG};
                border: none; border-radius: 14px;
            }}
            QPushButton:hover {{ background-color: {Color.PRIMARY_DARK}; }}
            QPushButton:pressed {{ background-color: {Color.PRIMARY_PRESSED}; }}
        """)
        start_btn.clicked.connect(lambda: self._nav("guest_assessment"))
        root.addWidget(start_btn, alignment=Qt.AlignCenter)

        guest_hint = QLabel("No account needed \u2014 start training right away")
        guest_hint.setAlignment(Qt.AlignCenter)
        guest_hint.setStyleSheet(
            f"font-size: 13px; color: {Color.TEXT_DISABLED};"
        )
        root.addSpacing(6)
        root.addWidget(guest_hint, alignment=Qt.AlignCenter)

        root.addSpacing(20)

        # ── Log In / Sign Up side by side ────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(16)

        _secondary_style = f"""
            QPushButton {{
                font-size: 19px; font-weight: 600;
                background-color: {Color.SURFACE}; color: {Color.TEXT};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {Color.SURFACE_HOVER};
                border-color: {Color.PRIMARY};
            }}
            QPushButton:pressed {{ background-color: {Color.SURFACE_LIGHT}; }}
        """

        login_btn = QPushButton("Log In")
        login_btn.setFixedSize(230, 56)
        login_btn.setStyleSheet(_secondary_style)
        login_btn.clicked.connect(lambda: self._nav("account_picker"))

        signup_btn = QPushButton("Sign Up")
        signup_btn.setFixedSize(230, 56)
        signup_btn.setStyleSheet(_secondary_style)
        signup_btn.clicked.connect(lambda: self._nav("signup"))

        btn_row.addWidget(login_btn)
        btn_row.addWidget(signup_btn)
        root.addLayout(btn_row)

        root.addStretch(3)

        # ── Bottom row: Phone Login button (bottom-right) ────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()
        qr_btn = QPushButton("Phone Login")
        qr_btn.setFixedSize(140, 40)
        qr_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 14px; font-weight: 600;
                background-color: {Color.SURFACE}; color: {Color.TEXT_SECONDARY};
                border: 1px solid {Color.BORDER_LIGHT}; border-radius: 10px;
            }}
            QPushButton:hover {{
                color: {Color.PRIMARY}; border-color: {Color.PRIMARY};
            }}
            QPushButton:pressed {{ background-color: {Color.SURFACE_HOVER}; }}
        """)
        qr_btn.clicked.connect(self._show_qr)
        bottom.addWidget(qr_btn)
        root.addLayout(bottom)

    def _show_qr(self) -> None:
        popup = _QrPopup(self)
        popup.exec()

    def _nav(self, page: str):
        if self._router:
            self._router.navigate(page)

    def on_enter(self, **kwargs: Any) -> None:
        pass

    def on_leave(self) -> None:
        pass
