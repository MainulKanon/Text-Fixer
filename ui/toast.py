"""Tiny non-activating tooltip for errors / success."""
from __future__ import annotations

import win32api
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel

from . import winstyle


class Toast(QLabel):
    def __init__(self) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWordWrap(True)
        self.setMaximumWidth(380)
        self.hwnd = winstyle.make_non_activating(self)
        self._timer = QTimer(self, singleShot=True, timeout=self.hide)

    def show_message(self, text: str, error: bool = True, anchor: tuple[int, int] | None = None,
                     ms: int = 5000) -> None:
        bg, fg = ("#D32F2F", "white") if error else ("#2E7D32", "white")
        self.setStyleSheet(f"QLabel {{ background:{bg}; color:{fg}; border-radius:6px; padding:6px 10px;"
                           f" font: 9pt 'Segoe UI'; }}")
        self.setText(text)
        self.adjustSize()
        self.show()
        x, y = anchor if anchor else win32api.GetCursorPos()
        w, h = winstyle.window_size(self.hwnd)
        wl, wt, wr, wb = winstyle.work_area(x, y)
        x = max(wl, min(x - w, wr - w))
        y = y + 6 if y + 6 + h <= wb else y - h - 40
        winstyle.move_physical(self.hwnd, x, max(wt, y))
        self._timer.start(ms)
