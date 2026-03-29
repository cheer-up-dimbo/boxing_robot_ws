"""BoxBunny Sound Manager -- low-latency WAV playback via QSoundEffect.

Preloads all sounds into memory at startup.  Priority system ensures
high-priority sounds (e.g. stimulus cues) are never masked by UI bleeps.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)

# Priority tiers -- higher number == higher priority
PRIORITY_MAP: Dict[str, int] = {
    "stimulus": 5,
    "bell": 4,
    "countdown": 3,
    "feedback": 2,
    "ui": 1,
}

# Default sound catalogue (name -> relative filename inside assets/sounds/)
DEFAULT_SOUNDS: Dict[str, str] = {
    "stimulus": "stimulus.wav",
    "bell_start": "bell_start.wav",
    "bell_end": "bell_end.wav",
    "countdown_tick": "countdown_tick.wav",
    "countdown_go": "countdown_go.wav",
    "hit_confirm": "hit_confirm.wav",
    "combo_complete": "combo_complete.wav",
    "miss": "miss.wav",
    "btn_press": "btn_press.wav",
    "nav_tick": "nav_tick.wav",
    "error": "error.wav",
}


class SoundManager:
    """Manages preloaded WAV sound effects with priority and per-sound toggles."""

    def __init__(self, assets_dir: Path) -> None:
        self._sounds_dir: Path = assets_dir / "sounds"
        self._effects: Dict[str, QSoundEffect] = {}
        self._enabled: Dict[str, bool] = {}
        self._master_volume: float = 0.8
        self._current_priority: int = 0
        self._preload_all()

    # ── Public API ──────────────────────────────────────────────────────

    def play(self, name: str) -> None:
        """Play a named sound effect, respecting priority and toggles."""
        if name not in self._effects:
            logger.warning("Sound '%s' not loaded -- skipping", name)
            return
        if not self._enabled.get(name, True):
            return

        priority = self._resolve_priority(name)
        if priority < self._current_priority:
            return  # a higher-priority sound is already playing

        effect = self._effects[name]
        effect.setVolume(self._master_volume)
        effect.play()
        self._current_priority = priority

    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 -- 1.0)."""
        self._master_volume = max(0.0, min(1.0, volume))

    def set_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable an individual sound."""
        self._enabled[name] = enabled

    def stop_all(self) -> None:
        """Stop every playing sound and reset priority."""
        for effect in self._effects.values():
            if effect.isPlaying():
                effect.stop()
        self._current_priority = 0

    # ── Internals ───────────────────────────────────────────────────────

    def _preload_all(self) -> None:
        """Preload every sound in the catalogue."""
        for name, filename in DEFAULT_SOUNDS.items():
            path = self._sounds_dir / filename
            if not path.exists():
                logger.warning("Sound file missing: %s -- '%s' will be silent", path, name)
                self._enabled[name] = False
                continue
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(path)))
            effect.setLoopCount(1)
            effect.setVolume(self._master_volume)
            effect.playingChanged.connect(self._on_playing_changed)
            self._effects[name] = effect
            self._enabled[name] = True

    def _resolve_priority(self, name: str) -> int:
        """Map a sound name to its priority tier."""
        for prefix, prio in PRIORITY_MAP.items():
            if name.startswith(prefix):
                return prio
        return 0

    def _on_playing_changed(self) -> None:
        """Reset current priority when all sounds finish."""
        if not any(e.isPlaying() for e in self._effects.values()):
            self._current_priority = 0
