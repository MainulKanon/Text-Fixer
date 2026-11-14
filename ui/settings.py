"""Settings window."""
from __future__ import annotations

import threading

import keyboard
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
                               QTabWidget, QVBoxLayout, QWidget)

from config import DEFAULT_MODES, DEFAULT_REPLY_PROMPT, DEFAULT_SYSTEM_PROMPT, config
from core import startup
from providers import PROVIDERS, ProviderError, clean_output, complete_with_model_fallback

from .fix_panel import FixPanel
from .icons import app_icon


class _Bridge(QObject):
    done = Signal(str, bool)   # message, ok
    hotkey = Signal(object, str)
    models = Signal(str, list)  # provider, model ids
    model = Signal(str, str)    # provider, model id (auto-switched)


class HotkeyEdit(QWidget):
    def __init__(self, value: str, bridge: _Bridge) -> None:
        super().__init__()
        self.bridge = bridge
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit(value)
        self.edit.setPlaceholderText("e.g. ctrl+shift+g")
        self.btn = QPushButton("Record")
        self.btn.clicked.connect(self._record)
        lay.addWidget(self.edit)
        lay.addWidget(self.btn)
        bridge.hotkey.connect(self._recorded)

    def _record(self) -> None:
        self.btn.setText("Press keys…")
        self.btn.setEnabled(False)
        threading.Thread(target=lambda: self.bridge.hotkey.emit(self, keyboard.read_hotkey(suppress=False)),
                         daemon=True).start()

    def _recorded(self, who, combo: str) -> None:
        if who is self:
            self.edit.setText(combo)
            self.btn.setText("Record")
            self.btn.setEnabled(True)

    def value(self) -> str:
        return self.edit.text().strip().lower()


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Text Fixer – Settings")
        self.setWindowIcon(app_icon())
        self.resize(640, 560)
        self.bridge = _Bridge()
        self.bridge.done.connect(self._test_done)
        self.bridge.models.connect(self._set_models)
        self.bridge.model.connect(self._set_model)

        self.tabs = tabs = QTabWidget()
        self.fix_panel = FixPanel()
        tabs.addTab(self.fix_panel, "✨ Paste && fix")
        tabs.addTab(self._providers_tab(), "AI providers")
        tabs.addTab(self._prompts_tab(), "Prompts")
        tabs.addTab(self._behavior_tab(), "Behavior")
        tabs.addTab(self._exclude_tab(), "Excluded apps")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        # Save/Cancel belong to the settings tabs, not to Paste & fix.
        tabs.currentChanged.connect(lambda i: buttons.setVisible(tabs.widget(i) is not self.fix_panel))
        buttons.setVisible(False)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(buttons)

    def show_tab(self, name: str) -> None:
        """'fix' opens Paste & fix; anything else opens AI providers."""
        self.tabs.setCurrentIndex(0 if name == "fix" else 1)
        if name == "fix":
            self.fix_panel.input.setFocus()

    # ---------- tabs ----------
    def _providers_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.key_edits, self.model_edits = {}, {}
        pconf = config.get("providers", {})
        for name, prov in PROVIDERS.items():
            box = QGroupBox(prov.label)
            f = QFormLayout(box)
            key = QLineEdit(pconf.get(name, {}).get("api_key", ""))
            key.setEchoMode(QLineEdit.Password)
            key.setPlaceholderText("Paste your API key")
            show = QPushButton("Show")
            show.setCheckable(True)
            show.toggled.connect(lambda on, k=key: k.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
            get = QPushButton("Get free key")
            get.clicked.connect(lambda _=False, u=prov.key_url: QDesktopServices.openUrl(QUrl(u)))
            test = QPushButton("Test")
            test.clicked.connect(lambda _=False, n=name: self._test(n))
            row = QHBoxLayout()
            row.addWidget(key, 1)
            row.addWidget(show)
            row.addWidget(get)
            row.addWidget(test)
            model = QComboBox()
            model.setEditable(True)
            model.setInsertPolicy(QComboBox.NoInsert)
            model.setEditText(pconf.get(name, {}).get("model", ""))
            refresh = QPushButton("↻ Load models")
            refresh.setToolTip("Fetch the models this API key can use")
            refresh.clicked.connect(lambda _=False, n=name: self._load_models(n))
            mrow = QHBoxLayout()
            mrow.addWidget(model, 1)
            mrow.addWidget(refresh)
            f.addRow("API key", row)
            f.addRow("Model", mrow)
            self.key_edits[name], self.model_edits[name] = key, model
            lay.addWidget(box)

        order_box = QGroupBox("Provider order (drag to reorder – first is default; next ones are fallbacks)")
        ol = QVBoxLayout(order_box)
        self.order = QListWidget()
        self.order.setDragDropMode(QAbstractItemView.InternalMove)
        self.order.setMaximumHeight(90)
        order = [n for n in config.get("provider_order", []) if n in PROVIDERS]
        order += [n for n in PROVIDERS if n not in order]
        for n in order:
            self.order.addItem(n)
        ol.addWidget(self.order)
        lay.addWidget(order_box)
        self.test_label = QLabel("")
        self.test_label.setWordWrap(True)
        lay.addWidget(self.test_label)
        lay.addStretch()
        return w

    def _prompts_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Main prompt (✨ click, hotkey, “Fix grammar” mode):"))
        self.system_prompt = QPlainTextEdit(config.get("system_prompt", DEFAULT_SYSTEM_PROMPT))
        self.system_prompt.setMaximumHeight(80)
        lay.addWidget(self.system_prompt)

        lay.addWidget(QLabel("Right-click modes – pick a mode to edit its prompt:"))
        self.modes = dict(config.get("modes", DEFAULT_MODES))
        self.modes.pop("Fix grammar", None)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(list(self.modes))
        self.mode_prompt = QPlainTextEdit()
        self.mode_prompt.setMaximumHeight(90)
        self._mode_current = None
        self.mode_combo.currentTextChanged.connect(self._mode_switch)
        self._mode_switch(self.mode_combo.currentText())
        lay.addWidget(self.mode_combo)
        lay.addWidget(self.mode_prompt)

        lay.addWidget(QLabel("Reply assistant prompt:"))
        self.reply_prompt = QPlainTextEdit(config.get("reply_prompt", DEFAULT_REPLY_PROMPT))
        self.reply_prompt.setMaximumHeight(110)
        lay.addWidget(self.reply_prompt)

        reset = QPushButton("Reset all prompts to defaults")
        reset.clicked.connect(self._reset_prompts)
        lay.addWidget(reset, alignment=Qt.AlignLeft)
        lay.addStretch()
        return w

    def _behavior_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self.show_button = QCheckBox("Show the floating ✨ button (off = hotkey-only mode)")
        self.show_button.setChecked(config.get("show_button", True))
        self.preview = QCheckBox("Show a preview first – replace only when I click Replace")
        self.preview.setChecked(config.get("preview_before_replace", True))
        self.hotkey = HotkeyEdit(config.get("hotkey", "ctrl+shift+g"), self.bridge)
        self.reply_hotkey = HotkeyEdit(config.get("reply_hotkey", "ctrl+shift+r"), self.bridge)
        self.min_chars = QSpinBox(minimum=1, maximum=500, value=int(config.get("min_chars", 5)))
        self.idle = QDoubleSpinBox(minimum=0.3, maximum=10, singleStep=0.1, value=float(config.get("idle_delay", 1.0)))
        self.idle.setSuffix(" s")
        self.hide_after = QDoubleSpinBox(minimum=2, maximum=120, singleStep=1, value=float(config.get("hide_after", 10)))
        self.hide_after.setSuffix(" s")
        self.autostart = QCheckBox("Start Text Fixer when Windows starts")
        self.autostart.setChecked(startup.is_enabled())
        f.addRow(self.show_button)
        f.addRow(self.preview)
        f.addRow("Fix hotkey", self.hotkey)
        f.addRow("Reply hotkey", self.reply_hotkey)
        f.addRow("Minimum characters", self.min_chars)
        f.addRow("Show button after typing pause", self.idle)
        f.addRow("Hide button after inactivity", self.hide_after)
        f.addRow(self.autostart)
        note = QLabel("Reply hotkey: select a message (email, chat…) and press it – Text Fixer drafts a reply. "
                      "If nothing is selected, it uses the text on your clipboard.")
        note.setWordWrap(True)
        f.addRow(note)
        return w

    def _exclude_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("The ✨ button never shows in these apps (one .exe name per line). "
                             "Password fields are always skipped."))
        self.excluded = QPlainTextEdit("\n".join(config.get("excluded_apps", [])))
        lay.addWidget(self.excluded)
        return w

    # ---------- actions ----------
    def _mode_switch(self, name: str) -> None:
        if self._mode_current is not None:
            self.modes[self._mode_current] = self.mode_prompt.toPlainText().strip()
        self._mode_current = name
        self.mode_prompt.setPlainText(self.modes.get(name, ""))

    def _reset_prompts(self) -> None:
        self.system_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT)
        self.reply_prompt.setPlainText(DEFAULT_REPLY_PROMPT)
        self.modes = {k: v for k, v in DEFAULT_MODES.items() if k != "Fix grammar"}
        self._mode_current = None
        self._mode_switch(self.mode_combo.currentText())

    def _test(self, name: str) -> None:
        key = self.key_edits[name].text().strip()
        model = self.model_edits[name].currentText().strip()
        if not key:
            self.test_label.setText(f"Enter a {PROVIDERS[name].label} key first.")
            return
        self.test_label.setStyleSheet("")
        self.test_label.setText(f"Testing {PROVIDERS[name].label}…")

        def work():
            prov = PROVIDERS[name]
            try:
                raw, used = complete_with_model_fallback(prov, key, model, DEFAULT_SYSTEM_PROMPT,
                                                         "i has send you the file yesterday, pls check it")
                note = f" (switched model to {used})" if used != model else ""
                if used != model:
                    self.bridge.model.emit(name, used)
                self.bridge.done.emit(f"✅ {prov.label} works{note}: “{clean_output(raw)}”", True)
            except ProviderError as e:
                self.bridge.done.emit(f"❌ {e}", False)
        threading.Thread(target=work, daemon=True).start()

    def _load_models(self, name: str) -> None:
        key = self.key_edits[name].text().strip()
        if not key:
            self.test_label.setText(f"Enter a {PROVIDERS[name].label} key first.")
            return
        self.test_label.setStyleSheet("")
        self.test_label.setText(f"Loading {PROVIDERS[name].label} models…")

        def work():
            prov = PROVIDERS[name]
            try:
                models = [m for m in prov.list_models(key)
                          if not any(w in m.lower() for w in prov.excluded_model_words)]
                self.bridge.models.emit(name, models)
                self.bridge.done.emit(f"Loaded {len(models)} {prov.label} models – pick one from the list.", True)
            except ProviderError as e:
                self.bridge.done.emit(f"❌ {e}", False)
        threading.Thread(target=work, daemon=True).start()

    def _set_models(self, name: str, models: list) -> None:
        box = self.model_edits[name]
        current = box.currentText()
        box.clear()
        box.addItems(models)
        box.setEditText(current if current in models or not models else (PROVIDERS[name].pick_model(models) or current))
        box.showPopup()

    def _set_model(self, name: str, model: str) -> None:
        self.model_edits[name].setEditText(model)

    def _test_done(self, msg: str, ok: bool) -> None:
        self.test_label.setStyleSheet("color:#2E7D32" if ok else "color:#C62828")
        self.test_label.setText(msg)

    def _save(self) -> None:
        for hk in (self.hotkey.value(), self.reply_hotkey.value()):
            try:
                keyboard.parse_hotkey(hk)
            except Exception:
                QMessageBox.warning(self, "Text Fixer", f"Invalid hotkey: {hk!r}")
                return
        self._mode_switch(self.mode_combo.currentText())

        providers = config.get("providers", {})
        for n in PROVIDERS:
            providers.setdefault(n, {})
            providers[n]["api_key"] = self.key_edits[n].text().strip()
            providers[n]["model"] = self.model_edits[n].currentText().strip()
        d = config.data
        d["providers"] = providers
        d["provider_order"] = [self.order.item(i).text() for i in range(self.order.count())]
        d["system_prompt"] = self.system_prompt.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT
        d["modes"] = {"Fix grammar": d["system_prompt"], **self.modes}
        d["reply_prompt"] = self.reply_prompt.toPlainText().strip() or DEFAULT_REPLY_PROMPT
        d["show_button"] = self.show_button.isChecked()
        d["preview_before_replace"] = self.preview.isChecked()
        d["hotkey"] = self.hotkey.value()
        d["reply_hotkey"] = self.reply_hotkey.value()
        d["min_chars"] = self.min_chars.value()
        d["idle_delay"] = self.idle.value()
        d["hide_after"] = self.hide_after.value()
        d["excluded_apps"] = [l.strip().lower() for l in self.excluded.toPlainText().splitlines() if l.strip()]
        d["start_with_windows"] = self.autostart.isChecked()
        config.save()
        try:
            startup.set_enabled(self.autostart.isChecked())
        except OSError as e:
            QMessageBox.warning(self, "Text Fixer", f"Could not update startup setting: {e}")
        self.saved.emit()
        self.accept()
