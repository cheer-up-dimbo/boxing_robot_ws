"""BoxBunny GUI -- main application entry point.

Creates the QApplication, wires up all subsystems via constructor injection,
and launches the 1024x600 frameless window for the Jetson Orin NX touchscreen.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from boxbunny_gui.gui_bridge import GuiBridge
from boxbunny_gui.nav.imu_nav_handler import ImuNavHandler, KeyboardNavFilter
from boxbunny_gui.nav.router import PageRouter
from boxbunny_gui.sound import SoundManager
from boxbunny_gui.theme import GLOBAL_STYLESHEET, Size

logger = logging.getLogger(__name__)

# Resolve asset directory relative to this file's package
_PKG_DIR = Path(__file__).resolve().parent
_SRC_DIR = _PKG_DIR.parent  # boxbunny_gui source root
_ASSETS_DIR = _SRC_DIR / "assets"


class BoxBunnyApp:
    """Top-level application object.

    Owns every subsystem and wires them together.
    No globals, no singletons -- everything is passed by reference.
    """

    def __init__(self, argv: Optional[list[str]] = None) -> None:
        self._setup_logging()

        # ── Qt application ──────────────────────────────────────────────
        self._qapp = QApplication(argv or sys.argv)
        self._qapp.setApplicationName("BoxBunny")
        self._qapp.setStyleSheet(GLOBAL_STYLESHEET)

        # ── Main window (frameless, fixed size) ─────────────────────────
        self._window = QMainWindow()
        self._window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self._window.setFixedSize(Size.SCREEN_W, Size.SCREEN_H)
        self._window.setWindowTitle("BoxBunny")

        # ── Central stacked widget for page routing ─────────────────────
        self._stack = QStackedWidget()
        self._window.setCentralWidget(self._stack)

        # ── Subsystems ──────────────────────────────────────────────────
        self._bridge = GuiBridge(parent=self._window)
        self._router = PageRouter(self._stack, parent=self._window)
        self._sound = SoundManager(self._resolve_assets_dir())
        self._imu_nav = ImuNavHandler(parent=self._window)

        # ── Keyboard nav filter (dev convenience) ───────────────────────
        self._kb_filter = KeyboardNavFilter(self._imu_nav, parent=self._window)
        self._window.installEventFilter(self._kb_filter)

        # ── Wire signals ────────────────────────────────────────────────
        self._connect_signals()

        # ── Register pages ──────────────────────────────────────────────
        self._register_pages()

        # ── Start ROS bridge (non-blocking) ─────────────────────────────
        self._bridge.start()

        logger.info("BoxBunnyApp initialised (online=%s)", self._bridge.online)

    # ── Public API ──────────────────────────────────────────────────────

    def run(self) -> int:
        """Show the window and enter the Qt event loop."""
        self._router.navigate("home")
        self._window.show()
        exit_code = self._qapp.exec()
        self._shutdown()
        return exit_code

    # ── Internals ───────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Wire bridge signals to subsystem handlers."""
        self._bridge.nav_command.connect(self._imu_nav.handle_command)
        self._bridge.session_state_changed.connect(
            self._imu_nav.on_session_state_changed
        )
        self._imu_nav.go_back.connect(self._router.back)

    def _register_pages(self) -> None:
        """Create and register all page widgets with the router.

        Each page receives its dependencies through its constructor -- no
        globals required.  Placeholder QWidgets are used for pages that
        have not yet been implemented.
        """
        # Shared deps dict for page factories
        deps = {
            "bridge": self._bridge,
            "router": self._router,
            "sound": self._sound,
            "imu_nav": self._imu_nav,
        }

        # Register placeholder pages for every expected route
        page_names = [
            "auth",
            "home",
            "training_select",
            "training_session",
            "sparring_select",
            "sparring_session",
            "performance",
            "history",
            "presets",
            "coach",
            "settings",
        ]
        for name in page_names:
            page = self._try_load_page(name, deps)
            self._router.register(name, page)

    def _try_load_page(self, name: str, deps: dict) -> QWidget:
        """Attempt to import and instantiate a page, falling back to a stub."""
        # Map route name -> module path and class name
        page_map = {
            "auth": ("boxbunny_gui.pages.auth", "AuthPage"),
            "home": ("boxbunny_gui.pages.home", "HomePage"),
            "training_select": ("boxbunny_gui.pages.training", "TrainingSelectPage"),
            "training_session": ("boxbunny_gui.pages.training", "TrainingSessionPage"),
            "sparring_select": ("boxbunny_gui.pages.sparring", "SparringSelectPage"),
            "sparring_session": ("boxbunny_gui.pages.sparring", "SparringSessionPage"),
            "performance": ("boxbunny_gui.pages.performance", "PerformancePage"),
            "history": ("boxbunny_gui.pages.history", "HistoryPage"),
            "presets": ("boxbunny_gui.pages.presets", "PresetsPage"),
            "coach": ("boxbunny_gui.pages.coach", "CoachPage"),
            "settings": ("boxbunny_gui.pages.settings", "SettingsPage"),
        }

        if name not in page_map:
            return self._make_placeholder(name)

        module_path, class_name = page_map[name]
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            return cls(**deps)
        except (ImportError, AttributeError):
            logger.debug("Page '%s' not yet implemented -- using placeholder", name)
            return self._make_placeholder(name)

    @staticmethod
    def _make_placeholder(name: str) -> QWidget:
        """Create a minimal stub widget for an unimplemented page."""
        from PySide6.QtWidgets import QLabel, QVBoxLayout
        from boxbunny_gui.theme import Color, font

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{name.replace('_', ' ').title()}")
        label.setFont(font(Size.TEXT_HEADER, bold=True))
        label.setStyleSheet(f"color: {Color.TEXT_SECONDARY};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        sub = QLabel("Coming soon")
        sub.setFont(font(Size.TEXT_BODY))
        sub.setStyleSheet(f"color: {Color.TEXT_DISABLED};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        return widget

    @staticmethod
    def _resolve_assets_dir() -> Path:
        """Find the assets directory, checking source tree then install share."""
        if _ASSETS_DIR.is_dir():
            return _ASSETS_DIR
        # Fallback: ament install share directory
        try:
            from ament_index_python.packages import get_package_share_directory
            share = Path(get_package_share_directory("boxbunny_gui"))
            assets = share / "assets"
            if assets.is_dir():
                return assets
        except Exception:
            pass
        logger.warning("Assets directory not found -- sounds will be silent")
        return _ASSETS_DIR

    @staticmethod
    def _setup_logging() -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def _shutdown(self) -> None:
        """Clean up subsystems on exit."""
        self._sound.stop_all()
        self._bridge.shutdown()
        logger.info("BoxBunnyApp shut down")


def main() -> None:
    """ROS 2 / console_scripts entry point."""
    app = BoxBunnyApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
