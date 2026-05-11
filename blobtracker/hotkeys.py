from __future__ import annotations

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget


class HotkeyManager:
    def __init__(self, host: QWidget) -> None:
        self.host = host
        self.shortcuts = []

    def register(self, key: str, callback) -> QShortcut:
        shortcut = QShortcut(QKeySequence(key), self.host)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)
        return shortcut

    def setup_defaults(self, on_play_pause, on_record_toggle, on_preset_browser, on_fullscreen) -> None:
        self.register("Space", on_play_pause)
        self.register("R", on_record_toggle)
        self.register("P", on_preset_browser)
        self.register("F", on_fullscreen)
