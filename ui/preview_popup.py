"""Preview card: shows the AI result (changes highlighted) before anything is replaced.

Non-activating, like the ✨ button, so keyboard focus stays in the user's text box and
"Replace" can paste straight into it.
"""
from __future__ import annotations

import difflib
import html
import math
import os
import re

import win32gui
import win32process
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QTextBrowser, QVBoxLayout,
                               QWidget)

from . import winstyle

WIDTH = 420
TEXT_W = WIDTH - 50   # card margins 14 + 12, border, and a little slack
MAX_TEXT_H = 240

CSS = """
#card { background:#FFFFFF; border:1px solid #D3D1C7; border-radius:12px; }
QLabel#title { color:#5F5E5A; font: 9pt 'Segoe UI'; }
QLabel#before { color:#888780; font: 9pt 'Segoe UI'; }
QLabel#hint { color:#888780; font: 8pt 'Segoe UI'; }
QTextBrowser { border:none; background:transparent; color:#2C2C2A; font: 10.5pt 'Segoe UI'; }
QPushButton { font: 9pt 'Segoe UI'; padding:5px 12px; border-radius:6px; border:1px solid #D3D1C7;
              background:#FFFFFF; color:#2C2C2A; }
QPushButton:hover { background:#F1EFE8; }
QPushButton:disabled { color:#B4B2A9; }
QPushButton#primary { background:#534AB7; border-color:#534AB7; color:#FFFFFF; font-weight:600; }
QPushButton#primary:hover { background:#3C3489; }
QPushButton#primary:disabled { background:#AFA9EC; border-color:#AFA9EC; }
QPushButton#close { border:none; padding:2px 6px; color:#888780; font-size:11pt; }
QPushButton#close:hover { background:#F1EFE8; color:#2C2C2A; }
QPushButton#mode { border:none; padding:2px 6px; color:#534AB7; }
QPushButton#mode:hover { background:#EEEDFE; }
"""

_TOKEN = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)


def diff_html(old: str, new: str) -> str:
    """New text as HTML with inserted/changed words highlighted green."""
    a, b = _TOKEN.findall(old), _TOKEN.findall(new)
    out = []
    for op, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        chunk = html.escape("".join(b[j1:j2]))
        if op in ("insert", "replace") and chunk.strip():
            out.append(f'<span style="background-color:#D7F2E5; color:#085041;">{chunk}</span>')
        else:
            out.append(chunk)
    return "".join(out).replace("\n", "<br>")


def _short(text: str, n: int = 140) -> str:
    t = " ".join(text.split())
    return t if len(t) <= n else t[: n - 1] + "…"


class PreviewPopup(QWidget):
    replace_clicked = Signal(dict)
    retry_clicked = Signal(dict)
    mode_chosen = Signal(dict, str)
    copy_clicked = Signal(str)
    closed = Signal()

    def __init__(self, mode_names_fn) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(CSS)
        self._mode_names = mode_names_fn
        self.info: dict = {}

        card = QFrame(objectName="card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        self.title = QLabel(objectName="title")
        self.mode_btn = QPushButton("Change style ▾", objectName="mode")
        self.mode_btn.setCursor(Qt.PointingHandCursor)
        self.mode_btn.clicked.connect(self._mode_menu)
        close = QPushButton("✕", objectName="close")
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip("Keep my text")
        close.clicked.connect(self.dismiss)
        head = QHBoxLayout()
        head.addWidget(self.title)
        head.addStretch()
        head.addWidget(self.mode_btn)
        head.addWidget(close)

        self.before = QLabel(objectName="before")
        self.before.setWordWrap(True)
        self.text = QTextBrowser()
        self.text.setOpenLinks(False)
        self.text.setFrameShape(QFrame.NoFrame)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.document().setDocumentMargin(0)

        self.replace_btn = QPushButton("Replace", objectName="primary")
        self.retry_btn = QPushButton("↻ Try again")
        self.copy_btn = QPushButton("Copy")
        for b in (self.replace_btn, self.retry_btn, self.copy_btn):
            b.setCursor(Qt.PointingHandCursor)
        self.replace_btn.clicked.connect(lambda: self._emit(self.replace_clicked))
        self.retry_btn.clicked.connect(lambda: self._emit(self.retry_clicked))
        self.copy_btn.clicked.connect(self._copy)
        self.hint = QLabel("Ctrl+Z undoes it afterwards", objectName="hint")
        foot = QHBoxLayout()
        foot.addWidget(self.replace_btn)
        foot.addWidget(self.retry_btn)
        foot.addWidget(self.copy_btn)
        foot.addStretch()
        foot.addWidget(self.hint)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 12, 12)
        lay.setSpacing(8)
        lay.addLayout(head)
        lay.addWidget(self.before)
        lay.addWidget(self.text)
        lay.addLayout(foot)

        self.setFixedWidth(WIDTH)
        self.hwnd = winstyle.make_non_activating(self)
        # Close automatically when the user switches to another app.
        self._watch = QTimer(self, interval=400, timeout=self._check_foreground)

    # never activate on click
    def nativeEvent(self, event_type, message):
        if winstyle.is_mouse_activate(message):
            return True, winstyle.MA_NOACTIVATE
        return super().nativeEvent(event_type, message)

    # ---------- content ----------
    def show_for(self, info: dict, anchor: tuple[int, int, int, int] | None) -> None:
        """anchor = physical rect (l, t, r, b) to sit next to (the button), or None for the mouse."""
        self.info = info
        self.title.setText(f"✨ {info['mode']}  ·  {info['label']}")
        self.before.setText(f"<s>{html.escape(_short(info['original']))}</s>")
        self.text.setHtml(diff_html(info["original"], info["fixed"]))
        self.set_busy(False)
        self._fit_text()
        self.adjustSize()
        if not self.isVisible():
            self.show()
        self._place(anchor)
        self._watch.start()

    def _fit_text(self) -> None:
        # Wrap at a FIXED width (narrower than the card's text area) so the height we measure is exactly
        # the height that gets drawn at any display scaling; otherwise the last line can be clipped.
        self.text.setLineWrapMode(QTextBrowser.FixedPixelWidth)
        self.text.setLineWrapColumnOrWidth(TEXT_W)
        doc = self.text.document()
        doc.setTextWidth(TEXT_W)
        h = int(math.ceil(doc.documentLayout().documentSize().height())) + 12
        self.text.setFixedHeight(min(max(h, 22), MAX_TEXT_H))

    def set_busy(self, busy: bool) -> None:
        for b in (self.replace_btn, self.retry_btn, self.copy_btn, self.mode_btn):
            b.setEnabled(not busy)
        self.replace_btn.setText("Working…" if busy else "Replace")

    def _place(self, anchor) -> None:
        w, h = winstyle.window_size(self.hwnd)
        if anchor:
            l, t, r, b = anchor
        else:
            import win32api
            x, y = win32api.GetCursorPos()
            l, t, r, b = x, y, x, y + 16
        wl, wt, wr, wb = winstyle.work_area(r, b)
        x = r - w                       # right-align with the button
        y = b + 6 if b + 6 + h <= wb else t - h - 6
        x = max(wl, min(x, wr - w))
        y = max(wt, min(y, wb - h))
        winstyle.move_physical(self.hwnd, x, y)

    # ---------- actions ----------
    def _emit(self, signal) -> None:
        if self.info:
            signal.emit(self.info)

    def _copy(self) -> None:
        self.copy_clicked.emit(self.info.get("fixed", ""))
        self.dismiss()

    def _mode_menu(self) -> None:
        menu = QMenu(self)
        for name in self._mode_names():
            act = menu.addAction(name, lambda n=name: self.mode_chosen.emit(self.info, n))
            if name == self.info.get("mode"):
                act.setEnabled(False)
        menu.exec(self.mode_btn.mapToGlobal(QPoint(0, self.mode_btn.height())))

    def dismiss(self) -> None:
        self._watch.stop()
        self.hide()
        self.closed.emit()

    def _check_foreground(self) -> None:
        fg = win32gui.GetForegroundWindow()
        if not fg or fg == self.info.get("hwnd"):
            return
        try:
            if win32process.GetWindowThreadProcessId(fg)[1] == os.getpid():
                return  # our own menu / window
        except Exception:
            return
        self.dismiss()

    def physical_rect(self) -> tuple[int, int, int, int]:
        return win32gui.GetWindowRect(self.hwnd)
