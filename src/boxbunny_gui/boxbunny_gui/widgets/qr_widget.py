"""QR code display widget for WiFi credentials and dashboard URLs.

Gracefully falls back to a text label if the ``qrcode`` library is not
installed.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from boxbunny_gui.theme import Color, Size

log = logging.getLogger(__name__)

try:
    import qrcode  # type: ignore[import-untyped]
    from qrcode.constants import ERROR_CORRECT_M  # type: ignore[import-untyped]

    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False
    log.warning("qrcode library not installed -- QRWidget will display text fallback")


class QRWidget(QWidget):
    """Renders a QR code as a ``QPixmap`` inside a ``QLabel``.

    Falls back to plain text when the ``qrcode`` package is unavailable.

    Parameters
    ----------
    size : int
        Side length in pixels (default 200).
    """

    def __init__(self, size: int = 200, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._payload: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel()
        self._label.setFixedSize(size, size)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"background-color: {Color.SURFACE}; border-radius: {Size.RADIUS}px;"
        )
        layout.addWidget(self._label)

    # -- public API -----------------------------------------------------------
    def set_payload(self, ssid: str, password: str, url: str) -> None:
        """Encode WiFi credentials and a dashboard URL into a QR code."""
        text = f"WIFI:T:WPA;S:{ssid};P:{password};;\n{url}"
        self.set_text(text)

    def set_text(self, raw_text: str) -> None:
        """Encode arbitrary text into a QR code."""
        self._payload = raw_text
        if not _HAS_QRCODE:
            self._label.setText(raw_text[:60])
            self._label.setStyleSheet(
                f"color: {Color.TEXT_SECONDARY}; font-size: 11px;"
                f" background-color: {Color.SURFACE};"
                f" border-radius: {Size.RADIUS}px; padding: 8px;"
            )
            return

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(raw_text)
        qr.make(fit=True)

        # Inverted colours for dark theme: white modules on dark background
        img = qr.make_image(fill_color="white", back_color=Color.SURFACE).convert("RGB")
        img = img.resize((self._size, self._size))

        data = img.tobytes()
        qimage = QImage(data, img.width, img.height, 3 * img.width, QImage.Format.Format_RGB888)
        self._label.setPixmap(QPixmap.fromImage(qimage).scaled(
            self._size, self._size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
