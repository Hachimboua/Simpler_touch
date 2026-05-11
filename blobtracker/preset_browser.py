from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from param_store import ParamStore


class PresetCard(QPushButton):
    def __init__(self, name: str, parent=None) -> None:
        super().__init__(parent)
        self.name = name
        self.setText(name)
        self.setMinimumSize(140, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("text-align: left; padding: 8px;")
        self._set_thumbnail()

    def _set_thumbnail(self) -> None:
        pix = QPixmap(140, 50)
        pix.fill(Qt.GlobalColor.black)
        painter = QPainter(pix)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawRect(1, 1, 138, 48)
        painter.drawText(8, 28, self.name)
        painter.end()
        self.setIconSize(pix.size())
        self.setIcon(QIcon(pix))


class PresetBrowserDialog(QDialog):
    def __init__(self, param_store: ParamStore, parent=None) -> None:
        super().__init__(parent)
        self.param_store = param_store
        self.selected: Optional[str] = None
        self.setWindowTitle("Preset Browser")
        self.resize(560, 360)

        root_layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.scroll.setWidget(self.grid_container)

        root_layout.addWidget(self.scroll)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        root_layout.addWidget(close_btn)

        self.refresh()

    def refresh(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        names = self.param_store.list_presets()
        row = 0
        col = 0
        for name in names:
            card = PresetCard(name)
            card.clicked.connect(lambda checked=False, n=name: self._select_preset(n))
            self.grid.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        if not names:
            self.grid.addWidget(QLabel("No presets found."), 0, 0)

    def _select_preset(self, name: str) -> None:
        self.selected = name
        self.accept()
