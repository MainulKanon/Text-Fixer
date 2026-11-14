"""Paste & fix: paste any text, pick a style, get the improved version to copy.

Used as the first tab of the Settings window (and opened from the tray menu).
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)

from config import config
from core import history
from providers import ProviderError, run_chain

from .preview_popup import diff_html

from core.replacer import ALTERNATIVE_HINT  # noqa: E402  (shared with the preview card's Try again)


class _Bridge(QObject):
    done = Signal(str, str, bool)   # text, provider label or error, ok


class FixPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        self._original = ""
        self._result = ""
        self.bridge = _Bridge()
        self.bridge.done.connect(self._done)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Paste or type your text here…")
        paste = QPushButton("Paste")
        paste.setToolTip("Replace the box with the clipboard text")
        paste.clicked.connect(lambda: self.input.setPlainText(QGuiApplication.clipboard().text()))
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)

        self.mode = QComboBox()
        self.mode.addItems(config.mode_names())
        self.fix_btn = QPushButton("✨ Fix  (Ctrl+Enter)")
        self.fix_btn.setDefault(True)
        self.fix_btn.clicked.connect(lambda: self.fix())

        self.output = QTextBrowser()
        self.output.setStyleSheet("QTextBrowser { font-size: 11pt; }")
        self.input.setStyleSheet("QPlainTextEdit { font-size: 11pt; }")
        self.output.setPlaceholderText("The improved text appears here, with changes highlighted in green.")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.retry_btn = QPushButton("↻ Try again")
        self.retry_btn.clicked.connect(lambda: self.fix(alternative=True))
        self.copy_btn = QPushButton("Copy result")
        self.copy_btn.clicked.connect(self._copy)
        self.use_btn = QPushButton("Edit this")
        self.use_btn.setToolTip("Move the result into the box above to keep working on it")
        self.use_btn.clicked.connect(self._use_result)
        for b in (self.retry_btn, self.copy_btn, self.use_btn):
            b.setEnabled(False)

        top = QHBoxLayout()
        top.addWidget(QLabel("Your text:"))
        top.addStretch()
        top.addWidget(paste)
        top.addWidget(clear)
        mid = QHBoxLayout()
        mid.addWidget(QLabel("Style:"))
        mid.addWidget(self.mode, 1)
        mid.addWidget(self.fix_btn)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.use_btn)
        bottom.addWidget(self.retry_btn)
        bottom.addWidget(self.copy_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.input, 2)
        lay.addLayout(mid)
        lay.addWidget(QLabel("Result:"))
        lay.addWidget(self.output, 3)
        lay.addLayout(bottom)

        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self, activated=self.fix, context=Qt.WidgetWithChildrenShortcut)

    # ---------- actions ----------
    def fix(self, alternative: bool = False) -> None:
        text = self.input.toPlainText().strip()
        if self._busy:
            return
        if not text:
            self._set_status("Paste some text first.", error=True)
            return
        mode = self.mode.currentText()
        system = config.prompt_for_mode(mode)
        if alternative and self._result and text == self._original:
            system += ALTERNATIVE_HINT.format(prev=self._result)
        self._original = text
        self._busy = True
        self._set_buttons()
        self._set_status(f"{mode}…")

        def work():
            try:
                out, label = run_chain(config, system, text)
                history.add(mode, text, out)
                self.bridge.done.emit(out, label, True)
            except ProviderError as e:
                self.bridge.done.emit("", str(e), False)
            except Exception as e:  # never crash the app
                self.bridge.done.emit("", f"Unexpected error: {e}", False)
        threading.Thread(target=work, daemon=True).start()

    def _done(self, text: str, info: str, ok: bool) -> None:
        self._busy = False
        if ok:
            self._result = text
            self.output.setHtml(diff_html(self._original, text))
            same = text.strip() == self._original.strip()
            self._set_status(f"Already looks good ({info})." if same else f"Done via {info}.")
        else:
            self._set_status(info, error=True)
        self._set_buttons()

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._result)
        self._set_status("Copied. Paste it anywhere with Ctrl+V.")

    def _use_result(self) -> None:
        self.input.setPlainText(self._result)
        self.input.setFocus()

    def _clear(self) -> None:
        self.input.clear()
        self.output.clear()
        self._result = ""
        self._set_status("")
        self._set_buttons()
        self.input.setFocus()

    def _set_buttons(self) -> None:
        has = bool(self._result) and not self._busy
        self.fix_btn.setEnabled(not self._busy)
        self.fix_btn.setText("Working…" if self._busy else "✨ Fix  (Ctrl+Enter)")
        for b in (self.retry_btn, self.copy_btn, self.use_btn):
            b.setEnabled(has)

    def _set_status(self, msg: str, error: bool = False) -> None:
        self.status.setStyleSheet("color:#C62828" if error else "")
        self.status.setText(msg)
