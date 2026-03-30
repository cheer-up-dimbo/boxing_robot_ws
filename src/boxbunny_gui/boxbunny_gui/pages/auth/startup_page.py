"""Startup page — first screen users see.

Clean, modern dark UI. Large buttons, clear hierarchy, no clutter.
QR popup for phone dashboard access via a small button in the corner.
The popup starts the dashboard server + localhost.run tunnel automatically
so the QR code works from any phone on any network.  When the user logs
in on the phone, the GUI auto-navigates to the home screen.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import urllib.request
from io import BytesIO
from pathlib import Path
from threading import Thread
from typing import Any

from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from boxbunny_gui.theme import Color, Size, close_btn_style

logger = logging.getLogger(__name__)

_URL_FILE = "/tmp/boxbunny_dashboard_url.txt"
_GUI_LOGIN_FILE = Path("/tmp/boxbunny_gui_login.json")
_WS_ROOT = Path(__file__).resolve().parents[5]  # boxing_robot_ws/
_DASHBOARD_SCRIPT = _WS_ROOT / "tools" / "dashboard_server.py"

# Module-level refs so subprocesses outlive the popup dialog
_dashboard_proc: subprocess.Popen | None = None
_tunnel_proc: subprocess.Popen | None = None


def _server_is_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8080/api/health", timeout=2)
        return True
    except Exception:
        return False


def _ensure_server() -> None:
    """Start the dashboard server if it isn't already running."""
    global _dashboard_proc  # noqa: PLW0603
    if _server_is_up():
        return
    logger.info("Starting dashboard server: %s", _DASHBOARD_SCRIPT)
    _dashboard_proc = subprocess.Popen(
        [sys.executable, str(_DASHBOARD_SCRIPT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(0.5)
        if _server_is_up():
            return
    logger.warning("Dashboard server did not respond in time")


def _start_tunnel() -> str | None:
    """Open a localhost.run SSH tunnel. Returns public https URL or None."""
    global _tunnel_proc  # noqa: PLW0603
    for attempt in range(3):
        if attempt > 0:
            logger.info("Tunnel retry %d/3", attempt + 1)
            time.sleep(2)
        _tunnel_proc = subprocess.Popen(
            [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-o", "ConnectTimeout=10",
                "-R", "80:localhost:8080", "nokey@localhost.run",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            line = _tunnel_proc.stdout.readline().decode("utf-8", errors="ignore")
            if not line:
                break
            if ".lhr.life" in line:
                for word in line.split():
                    if word.startswith("https://"):
                        url = word.strip().rstrip(",")
                        logger.info("Tunnel URL: %s", url)
                        return url
        _tunnel_proc.terminate()
        try:
            _tunnel_proc.wait(timeout=3)
        except Exception:
            _tunnel_proc.kill()
    return None


class _TunnelSignals(QObject):
    """Signals emitted from the background tunnel thread."""
    url_ready = Signal(str)


class _QrPopup(QDialog):
    """QR code popup that auto-starts dashboard + tunnel.

    Polls ``/tmp/boxbunny_gui_login.json`` for a phone login event
    and accepts with ``login_info`` set so the caller can auto-navigate.
    """

    login_info: dict | None = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan QR Code")
        self.setFixedSize(500, 520)
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

        # QR code area — shows spinner text until tunnel is ready
        self._qr_label = QLabel("Connecting...")
        self._qr_label.setAlignment(Qt.AlignCenter)
        self._qr_label.setFixedSize(300, 300)
        self._qr_label.setStyleSheet(
            f"color: {Color.TEXT_SECONDARY}; font-size: 18px;"
        )
        layout.addWidget(self._qr_label, alignment=Qt.AlignCenter)

        self._url_label = QLabel("Setting up public URL...")
        self._url_label.setAlignment(Qt.AlignCenter)
        self._url_label.setStyleSheet(
            f"font-size: 14px; color: {Color.TEXT_SECONDARY}; font-weight: 600;"
        )
        self._url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._url_label)

        self._hint = QLabel("Starting dashboard server and tunnel...")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet(
            f"font-size: 14px; color: {Color.TEXT_SECONDARY};"
        )
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

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

        # Clear any stale login file before we start waiting
        try:
            _GUI_LOGIN_FILE.unlink(missing_ok=True)
        except OSError:
            pass

        # Start server + tunnel in background thread
        self._signals = _TunnelSignals()
        self._signals.url_ready.connect(self._on_url_ready)
        self._worker = Thread(target=self._setup_tunnel, daemon=True)
        self._worker.start()

        # Poll for phone login (every 1 second)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_phone_login)
        self._poll_timer.start(1000)

    def _setup_tunnel(self) -> None:
        """Background: ensure server is up, open tunnel, emit URL."""
        _ensure_server()

        # Check if tunnel URL already exists (from notebook cell 2)
        try:
            with open(_URL_FILE) as f:
                existing = f.read().strip()
            if existing.startswith("https://"):
                self._signals.url_ready.emit(existing)
                return
        except OSError:
            pass

        url = _start_tunnel()
        if url:
            try:
                with open(_URL_FILE, "w") as f:
                    f.write(url)
            except OSError:
                pass
            self._signals.url_ready.emit(url)
        else:
            # Tunnel failed — fall back to local URL from the URL file
            fallback = "http://localhost:8080"
            try:
                with open(_URL_FILE) as f:
                    fallback = f.read().strip() or fallback
            except OSError:
                pass
            self._signals.url_ready.emit(fallback)

    def _on_url_ready(self, url: str) -> None:
        """Called on main thread when the public URL is available."""
        self._url_label.setText(url)
        self._url_label.setStyleSheet(
            f"font-size: 16px; color: {Color.PRIMARY}; font-weight: 600;"
        )
        self._hint.setText("Scan the QR code or visit the URL to log in")

        try:
            import qrcode

            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="white", back_color=Color.BG)
            buf = BytesIO()
            img.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())
            self._qr_label.setPixmap(
                pix.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self._qr_label.setStyleSheet("")
        except ImportError:
            self._qr_label.setText(
                "QR code library not installed\npip install qrcode pillow"
            )
            self._qr_label.setStyleSheet(
                f"color: {Color.DANGER}; font-size: 14px;"
            )

    def _check_phone_login(self) -> None:
        """Poll for a login event written by the dashboard auth API."""
        try:
            data = json.loads(_GUI_LOGIN_FILE.read_text())
            username = data.get("username")
            if not username:
                return
            logger.info("Phone login detected: %s", username)
            self._poll_timer.stop()
            self.login_info = data
            # Clean up the file so it doesn't trigger again
            _GUI_LOGIN_FILE.unlink(missing_ok=True)
            self.accept()
        except (OSError, json.JSONDecodeError):
            pass


class StartupPage(QWidget):
    """Landing screen — branding + clear entry points."""

    def __init__(self, router=None, **kwargs):
        super().__init__()
        self._router = router

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(80, 24, 80, 24)

        # ── Close button (top-right) ─────────────────────────────────────
        close_btn = QPushButton("Close")
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
        if popup.exec() and popup.login_info:
            info = popup.login_info
            logger.info(
                "Auto-login from phone: %s (%s)",
                info.get("username"), info.get("user_type"),
            )
            if self._router:
                self._router.navigate(
                    "home",
                    user_id=info.get("user_id"),
                    username=info.get("username", "Guest"),
                )

    def _nav(self, page: str):
        if self._router:
            self._router.navigate(page)

    def on_enter(self, **kwargs: Any) -> None:
        pass

    def on_leave(self) -> None:
        pass
