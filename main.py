"""Text Fixer – fix grammar anywhere on Windows with one click.

Run:  .venv\\Scripts\\pythonw main.py     (or python main.py to see logs)
"""
from __future__ import annotations

import sys

import keyboard
import win32api
import win32event
import winerror
from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from config import CONFIG_PATH, config
from core.focus_watcher import FocusWatcher
from core.replacer import Fixer
from ui.floating_button import FloatingButton
from ui.history_window import HistoryWindow
from ui.icons import app_icon
from ui.preview_popup import PreviewPopup
from ui.reply_window import ReplyWindow
from ui.settings import SettingsDialog
from ui.toast import Toast


class FixItApp(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.fixer = Fixer()
        self.button = FloatingButton()
        self.toast = Toast()
        self.reply_win = ReplyWindow()
        self.history_win = HistoryWindow()
        self.settings_win: SettingsDialog | None = None
        self._last_from_hotkey = False
        self._last_anchor = None
        self._preview_anchor = None
        self._hotkeys = []

        # Fix action signals
        self.fixer.busy_changed.connect(self._on_busy)
        self.fixer.failed.connect(self._on_failed)
        self.fixer.succeeded.connect(self._on_success)
        self.fixer.selection_grabbed.connect(lambda text, hwnd: self.reply_win.open_with(text, hwnd))
        self.fixer.preview_ready.connect(self._show_preview)

        # Preview card (shown before replacing)
        self.preview = PreviewPopup(config.mode_names)
        self.preview.replace_clicked.connect(self._apply_preview)
        self.preview.retry_clicked.connect(lambda info: self.fixer.regenerate(info))
        self.preview.mode_chosen.connect(lambda info, mode: self.fixer.regenerate(info, mode))
        self.preview.copy_clicked.connect(self._copy_result)

        # Floating button
        self.button.clicked.connect(lambda: self.run_fix("Fix grammar"))
        self.button.right_clicked.connect(self._mode_menu)
        self.button.done_finished.connect(self._hide_button)
        self.watcher = FocusWatcher(self.fixer)
        self.button.hover_changed.connect(lambda h: setattr(self.watcher, "hover", h))
        self.watcher.show_request.connect(lambda info: None if self.preview.isVisible() else self.button.place(info))
        self.watcher.hide_request.connect(self._hide_button)
        self.watcher.start()

        self._build_tray()
        self.register_hotkeys()

        if not any((p.get("api_key") or "").strip() for p in config.get("providers", {}).values()):
            self.tray.showMessage("Text Fixer is running", "Add a free Groq API key to get started.",
                                  QSystemTrayIcon.Information, 6000)
            self.open_settings()
        else:
            self.tray.showMessage("Text Fixer is running",
                                  f"Type anywhere and click ✨, or press {config.get('hotkey')}.",
                                  QSystemTrayIcon.Information, 3000)

    # ---------- tray ----------
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(config.get("paused")), self.app)
        menu = QMenu()
        menu.addAction("✨ Paste && fix…", lambda: self.open_settings("fix"))
        menu.addAction("Reply assistant…", lambda: self.reply_win.open_with(QGuiApplication.clipboard().text(), 0,
                                                                            auto_generate=False))
        menu.addAction("History…", self._show_history)
        menu.addAction("Settings…", self.open_settings)
        menu.addSeparator()
        self.pause_action = QAction("Resume" if config.get("paused") else "Pause", menu)
        self.pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(self.pause_action)
        menu.addAction("Open config folder", lambda: __import__("os").startfile(CONFIG_PATH.parent))
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        # Double-click the tray icon → Paste & fix (the quickest way to fix any text).
        self.tray.activated.connect(lambda r: self.open_settings("fix") if r == QSystemTrayIcon.DoubleClick else None)
        self._update_tray()
        self.tray.show()

    def _update_tray(self) -> None:
        paused = config.get("paused")
        self.tray.setIcon(app_icon(paused))
        self.pause_action.setText("Resume" if paused else "Pause")
        self.tray.setToolTip(f"Text Fixer – {'paused' if paused else 'active'}\n"
                             f"Fix: {config.get('hotkey')}   Reply: {config.get('reply_hotkey')}")

    def toggle_pause(self) -> None:
        config.set("paused", not config.get("paused"))
        if config.get("paused"):
            self._hide_button()
        self._update_tray()

    def _show_history(self) -> None:
        self.history_win.show()
        self.history_win.raise_()
        self.history_win.activateWindow()

    def open_settings(self, tab: str = "providers") -> None:
        if not (self.settings_win and self.settings_win.isVisible()):
            self.settings_win = SettingsDialog()
            self.settings_win.saved.connect(self._settings_saved)
            self.settings_win.show()
        self.settings_win.show_tab(tab)
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def _settings_saved(self) -> None:
        self.register_hotkeys()
        self._update_tray()
        if not config.get("show_button"):
            self._hide_button()

    # ---------- hotkeys ----------
    def register_hotkeys(self) -> None:
        for h in self._hotkeys:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._hotkeys = []
        for combo, cb in ((config.get("hotkey"), self._hotkey_fix), (config.get("reply_hotkey"), self._hotkey_reply)):
            if not combo:
                continue
            try:
                self._hotkeys.append(keyboard.add_hotkey(combo, cb))
            except Exception as e:
                self.toast.show_message(f"Could not register hotkey {combo}: {e}")

    def _hotkey_fix(self) -> None:  # keyboard thread
        if not config.get("paused"):
            self._last_from_hotkey = True
            self.fixer.fix("Fix grammar", from_hotkey=True)

    def _hotkey_reply(self) -> None:  # keyboard thread
        if not config.get("paused"):
            self.fixer.grab_selection(from_hotkey=True)

    # ---------- fix ----------
    def run_fix(self, mode: str) -> None:
        self._last_from_hotkey = False
        # If the right-click menu took the foreground, the fixer brings the target window back first.
        self.fixer.fix(mode, target_hwnd=self.button.target_hwnd)

    def _mode_menu(self, pos) -> None:
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background:#FFFFFF; border:1px solid #D3D1C7; border-radius:8px; padding:4px; "
            "font: 9pt 'Segoe UI'; color:#2C2C2A; }"
            "QMenu::item { padding:6px 18px 6px 12px; border-radius:5px; }"
            "QMenu::item:selected { background:#EEEDFE; color:#26215C; }"
            "QMenu::separator { height:1px; background:#E5E3DC; margin:4px 6px; }")
        for name in config.mode_names():
            menu.addAction(("✨ " if name == "Fix grammar" else "") + name, lambda n=name: self.run_fix(n))
        menu.addSeparator()
        menu.addAction("💬 Reply to clipboard text…",
                       lambda: self.reply_win.open_with(QGuiApplication.clipboard().text(), self.button.target_hwnd))
        menu.addAction("Hide button", self._hide_button)
        menu.exec(pos)

    def _on_busy(self, busy: bool) -> None:
        if self.preview.isVisible():
            self.preview.set_busy(busy)
        elif self.button.isVisible():
            self.button.set_busy(busy)

    def _anchor(self):
        if self.preview.isVisible():
            l, t, r, b = self.preview.physical_rect()
            return r, b
        if self._last_anchor:
            return self._last_anchor
        return self.button.physical_anchor() if self.button.isVisible() and not self._last_from_hotkey else None

    # ---------- preview ----------
    def _show_preview(self, info: dict) -> None:
        anchor = None
        if self.button.isVisible() and not self._last_from_hotkey:
            import win32gui
            anchor = win32gui.GetWindowRect(self.button.hwnd)
            if self.button.last_field:
                # Button sits above the field → open the card below the field, not over the text.
                fl, ft, fr, fb = self.button.last_field
                bl, bt, br, bb = anchor
                anchor = (min(bl, fl), min(bt, ft), max(br, fr), max(bb, fb))
        elif self.preview.isVisible():
            anchor = None if not self.preview.info else self._preview_anchor
        self._preview_anchor = anchor
        self.button.reset()
        self.button.hide()
        self.preview.show_for(info, anchor)

    def _apply_preview(self, info: dict) -> None:
        l, t, r, b = self.preview.physical_rect()
        self._last_anchor = (r, t + 40)
        self.preview.dismiss()
        self.fixer.apply(info)

    def _copy_result(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)
        self.toast.show_message("Copied – paste it with Ctrl+V", error=False, ms=1600)

    def _on_failed(self, msg: str) -> None:
        self.toast.show_message(msg, error=True, anchor=self._anchor())
        self._last_anchor = None

    def _on_success(self, label: str) -> None:
        if "already looks good" in label:
            self.toast.show_message(f"✓ {label} – no changes needed", error=False, anchor=self._anchor(), ms=2200)
        elif self.button.isVisible() and not self._last_from_hotkey:
            self.button.show_done()      # green "Fixed · Ctrl+Z to undo", then hides
        else:
            self.toast.show_message("✓ Replaced – Ctrl+Z to undo", error=False, anchor=self._anchor(), ms=1800)
        self._last_anchor = None

    def _hide_button(self) -> None:
        if not self.fixer.busy:
            self.button.reset()
            self.button.hide()

    def quit(self) -> None:
        self.watcher.stop()
        keyboard.unhook_all()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    mutex = win32event.CreateMutex(None, False, "Global\\FixIt_single_instance")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        app = QApplication(sys.argv)
        QMessageBox.information(None, "Text Fixer", "Text Fixer is already running (see the system tray).")
        return 0
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Text Fixer")
    app.setWindowIcon(app_icon())
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Text Fixer", "No system tray available.")
        return 1
    _fixit = FixItApp(app)
    code = app.exec()
    del mutex
    return code


if __name__ == "__main__":
    sys.exit(main())
