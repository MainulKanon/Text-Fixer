"""Reply assistant: paste/select a message you received → get a reply draft."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from config import REPLY_TONES, config
from core import history
from core.replacer import paste_into
from providers import ProviderError, run_chain

from .icons import app_icon

TONE_HINTS = {
    "Professional": "Tone: professional, clear and polite.",
    "Friendly": "Tone: warm and friendly, still professional.",
    "Short": "Keep it short: 1–3 sentences.",
    "Detailed": "Make it thorough and helpful, covering every point in detail.",
    "Polite decline": "Politely decline the request while staying positive and professional.",
}


class _Bridge(QObject):
    done = Signal(str, str, bool)  # text, provider/err, ok


class ReplyWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Text Fixer – Reply assistant")
        self.setWindowIcon(app_icon())
        self.resize(560, 600)
        self.target_hwnd = 0
        self._busy = False
        self.bridge = _Bridge()
        self.bridge.done.connect(self._done)

        self.message = QPlainTextEdit()
        self.message.setPlaceholderText("Paste or select the message you received (email, Fiverr, WhatsApp…)")
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Optional: what you want to say, e.g. “yes, deliver by Friday, price $50”")
        self.tone = QComboBox()
        self.tone.addItems(REPLY_TONES)
        self.generate_btn = QPushButton("✨ Generate reply  (Ctrl+Enter)")
        self.generate_btn.setDefault(True)
        self.generate_btn.clicked.connect(self.generate)
        paste_btn = QPushButton("Paste")
        paste_btn.setToolTip("Replace the message with the clipboard text")
        paste_btn.clicked.connect(lambda: self.message.setPlainText(QGuiApplication.clipboard().text()))

        self.reply = QPlainTextEdit()
        self.reply.setPlaceholderText("Your reply will appear here – you can edit it before using it.")
        self.status = QLabel("")
        self.status.setWordWrap(True)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self._copy)
        self.insert_btn = QPushButton("Insert into app")
        self.insert_btn.setToolTip("Paste the reply into the window you came from (click into its reply box first)")
        self.insert_btn.clicked.connect(self._insert)

        top = QHBoxLayout()
        top.addWidget(QLabel("Message received:"))
        top.addStretch()
        top.addWidget(paste_btn)
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Tone:"))
        opts.addWidget(self.tone)
        opts.addStretch()
        opts.addWidget(self.generate_btn)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.copy_btn)
        bottom.addWidget(self.insert_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.message, 2)
        lay.addWidget(self.notes)
        lay.addLayout(opts)
        lay.addWidget(QLabel("Reply:"))
        lay.addWidget(self.reply, 3)
        lay.addLayout(bottom)

        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self, activated=self.generate)
        QShortcut(QKeySequence("Escape"), self, activated=self.hide)

    def open_with(self, text: str, hwnd: int = 0, auto_generate: bool = True) -> None:
        self.target_hwnd = hwnd
        self.insert_btn.setEnabled(bool(hwnd))
        if text.strip():
            self.message.setPlainText(text.strip())
            self.reply.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        if text.strip() and auto_generate:
            self.generate()
        else:
            self.message.setFocus()

    def generate(self) -> None:
        msg = self.message.toPlainText().strip()
        if self._busy:
            return
        if not msg:
            self._set_status("Paste the message you want to reply to first.", False)
            return
        self._busy = True
        self.generate_btn.setEnabled(False)
        self._set_status("Writing reply…", True)
        system = f"{config.get('reply_prompt')}\n\n{TONE_HINTS.get(self.tone.currentText(), '')}"
        user = f"Message I received:\n<<<\n{msg}\n>>>"
        notes = self.notes.text().strip()
        if notes:
            user += f"\n\nWhat I want to say in my reply (use this): {notes}"

        def work():
            try:
                text, label = run_chain(config, system, user)
                history.add(f"Reply ({self.tone.currentText()})", msg, text)
                self.bridge.done.emit(text, label, True)
            except ProviderError as e:
                self.bridge.done.emit("", str(e), False)
            except Exception as e:
                self.bridge.done.emit("", f"Unexpected error: {e}", False)
        threading.Thread(target=work, daemon=True).start()

    def _done(self, text: str, info: str, ok: bool) -> None:
        self._busy = False
        self.generate_btn.setEnabled(True)
        if ok:
            self.reply.setPlainText(text)
            self._set_status(f"Done via {info}. Edit if needed, then Copy or Insert.", True)
        else:
            self._set_status(info, False)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.reply.toPlainText())
        self._set_status("Copied to clipboard.", True)

    def _insert(self) -> None:
        text = self.reply.toPlainText().strip()
        if not text:
            return
        self.hide()
        hwnd = self.target_hwnd

        def work():
            ok = paste_into(hwnd, text)
            if not ok:
                self.bridge.done.emit(text, "Couldn't switch back – reply is on your clipboard (Ctrl+V).", False)
        threading.Thread(target=work, daemon=True).start()

    def _set_status(self, msg: str, ok: bool) -> None:
        self.status.setStyleSheet("color:#555" if ok else "color:#C62828")
        self.status.setText(msg)
