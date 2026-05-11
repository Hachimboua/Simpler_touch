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
        self.setMinimumSize(160, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.thumb = QLabel()
        self.thumb.setFixedSize(150, 60)
        self.thumb.setStyleSheet("background: #2a2a2a; border-radius: 4px;")
        
        self.title = QLabel(name)
        self.title.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.thumb)
        layout.addWidget(self.title)
        
        self.setStyleSheet("""
            PresetCard {
                background: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
            }
            PresetCard:hover {
                background: #2a2a2a;
                border: 1px solid #00e5ff;
            }
        """)
        self._set_thumbnail()

    def _set_thumbnail(self) -> None:
        pix = QPixmap(150, 60)
        pix.fill(QColor("#1a1a1a"))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#00e5ff"))
        # Draw some abstract representation of a preset
        painter.drawRect(10, 10, 130, 40)
        painter.setPen(QColor("#444444"))
        for i in range(3):
            painter.drawLine(20, 20 + i*10, 130, 20 + i*10)
        painter.end()
        self.thumb.setPixmap(pix)


class PresetBrowserDialog(QDialog):
    def __init__(self, param_store: ParamStore, parent=None) -> None:
        super().__init__(parent)
        self.param_store = param_store
        self.selected: Optional[str] = None
        self.setWindowTitle("Preset Browser")
        self.resize(600, 450)
        self.setStyleSheet("background: #121212;")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(15)
        
        title = QLabel("Select a Preset")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00e5ff;")
        root_layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(15)
        self.scroll.setWidget(self.grid_container)

        root_layout.addWidget(self.scroll)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("Cancel")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        root_layout.addLayout(btn_layout)

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
