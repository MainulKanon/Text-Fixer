"""Shows the last 20 fixes/replies."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QPlainTextEdit, QPushButton, QSplitter,
                               QVBoxLayout, QWidget)

from core import history

from .icons import app_icon


class HistoryWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.Window)
        self.setWindowTitle("Text Fixer – History")
        self.setWindowIcon(app_icon())
        self.resize(760, 460)
        self.items: list[dict] = []

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._select)
        self.original = QPlainTextEdit(readOnly=True)
        self.fixed = QPlainTextEdit(readOnly=True)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Original"))
        rl.addWidget(self.original)
        rl.addWidget(QLabel("Result"))
        rl.addWidget(self.fixed)
        row = QHBoxLayout()
        b1 = QPushButton("Copy original")
        b1.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.original.toPlainText()))
        b2 = QPushButton("Copy result")
        b2.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.fixed.toPlainText()))
        b3 = QPushButton("Clear history")
        b3.clicked.connect(self._clear)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch()
        row.addWidget(b3)
        rl.addLayout(row)

        split = QSplitter()
        split.addWidget(self.list)
        split.addWidget(right)
        split.setSizes([260, 500])
        QVBoxLayout(self).addWidget(split)

    def refresh(self) -> None:
        self.items = history.load()
        self.list.clear()
        for it in self.items:
            preview = it.get("original", "").replace("\n", " ")[:40]
            self.list.addItem(f"{it.get('time', '')} · {it.get('mode', '')}\n{preview}")
        if self.items:
            self.list.setCurrentRow(0)
        else:
            self.original.clear()
            self.fixed.clear()

    def _select(self, row: int) -> None:
        if 0 <= row < len(self.items):
            self.original.setPlainText(self.items[row].get("original", ""))
            self.fixed.setPlainText(self.items[row].get("fixed", ""))

    def _clear(self) -> None:
        history.clear()
        self.refresh()

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)
