"""The fix action: copy all text from the focused field → AI → paste back.

Also the "grab selection" helper used by the Reply assistant.
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Signal

from config import config
from providers import ProviderError, run_chain

from . import clipboard, history, keys


ALTERNATIVE_HINT = ("\n\nThe user didn't like this previous version:\n<<<\n{prev}\n>>>\n"
                    "Write a clearly different alternative: use different words, a different opening and a "
                    "different sentence structure. Keep the same meaning, tone and rules. Do not repeat the "
                    "previous version.")


class Fixer(QObject):
    busy_changed = Signal(bool)
    failed = Signal(str)
    succeeded = Signal(str)          # provider label
    preview_ready = Signal(dict)     # {original, fixed, label, mode, hwnd}
    selection_grabbed = Signal(str, int)  # text, hwnd (for the Reply window)

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.busy = False

    def _run(self, target, *args) -> None:
        """Run target in a worker thread, one job at a time, with busy signals and error handling."""
        if not self._lock.acquire(blocking=False):
            return

        def wrapper():
            self.busy = True
            self.busy_changed.emit(True)
            try:
                target(*args)
            except ProviderError as e:
                self.failed.emit(str(e))
            except Exception as e:  # never crash the background app
                self.failed.emit(f"Unexpected error: {e}")
            finally:
                self.busy = False
                self.busy_changed.emit(False)
                self._lock.release()
        threading.Thread(target=wrapper, daemon=True).start()

    # ---------- Fix: copy → AI → preview (or replace right away) ----------
    def fix(self, mode: str = "Fix grammar", from_hotkey: bool = False, target_hwnd: int = 0) -> None:
        self._run(self._fix_job, mode, from_hotkey, target_hwnd)

    def _fix_job(self, mode: str, from_hotkey: bool, target_hwnd: int) -> None:
        if from_hotkey:
            keys.wait_modifiers_released()
        if target_hwnd and keys.foreground() != target_hwnd:
            keys.focus_window(target_hwnd)
        hwnd = keys.foreground()

        saved = clipboard.snapshot()
        try:
            text = self._copy(select_all=True)
        finally:
            clipboard.restore(saved)
        if not text.strip():
            raise ProviderError("No text found in this field.")

        fixed, label = run_chain(config, config.prompt_for_mode(mode), text)
        if fixed.strip() == text.strip():
            self.succeeded.emit(f"{label}: already looks good")
            return
        info = {"original": text, "fixed": fixed, "label": label, "mode": mode, "hwnd": hwnd}
        if config.get("preview_before_replace", True):
            self.preview_ready.emit(info)
        else:
            self._apply_job(info, verify=False)

    # ---------- From the preview ----------
    def apply(self, info: dict) -> None:
        """User clicked Replace in the preview."""
        self._run(self._apply_job, info, True)

    def regenerate(self, info: dict, mode: str | None = None) -> None:
        """Try again (different wording) or switch to another mode, without touching the text field."""
        self._run(self._regen_job, info, mode)

    def _regen_job(self, info: dict, mode: str | None) -> None:
        new_mode = mode or info["mode"]
        system = config.prompt_for_mode(new_mode)
        if mode is None:  # "Try again"
            system += ALTERNATIVE_HINT.format(prev=info["fixed"])
        fixed, label = run_chain(config, system, info["original"])
        self.preview_ready.emit({**info, "fixed": fixed, "label": label, "mode": new_mode})

    def _apply_job(self, info: dict, verify: bool) -> None:
        hwnd, original, fixed = info["hwnd"], info["original"], info["fixed"]
        if hwnd and keys.foreground() != hwnd and not keys.focus_window(hwnd):
            raise ProviderError("Couldn't switch back to your text box – text not replaced.")
        saved = clipboard.snapshot()
        try:
            if verify:
                # The user may have kept typing while reading the preview; never overwrite new text.
                current = self._copy(select_all=True)
                if current.strip() != original.strip():
                    raise ProviderError("Your text changed since the preview – nothing was replaced. "
                                        "Click Fix again.")
            clipboard.set_text(fixed)
            time.sleep(0.05)
            keys.send("ctrl+a", 0.05)
            keys.send("ctrl+v", 0.25)  # give the app time to read the clipboard
        finally:
            time.sleep(0.1)
            clipboard.restore(saved)
        history.add(info["mode"], original, fixed)
        self.succeeded.emit(info["label"])

    # ---------- Grab selection (for Reply) ----------
    def grab_selection(self, from_hotkey: bool = True) -> None:
        if not self._lock.acquire(blocking=False):
            return
        threading.Thread(target=self._grab_worker, args=(from_hotkey,), daemon=True).start()

    def _grab_worker(self, from_hotkey: bool) -> None:
        saved = clipboard.snapshot()
        previous_text = clipboard.get_text()
        text = ""
        hwnd = 0
        try:
            if from_hotkey:
                keys.wait_modifiers_released()
            hwnd = keys.foreground()
            text = self._copy(select_all=False)
        except Exception:
            pass
        finally:
            clipboard.restore(saved)
            self._lock.release()
        # Nothing selected → fall back to whatever text was already on the clipboard.
        self.selection_grabbed.emit(text or previous_text or "", hwnd)

    # ---------- helpers ----------
    @staticmethod
    def _copy(select_all: bool) -> str:
        seq = clipboard.sequence()
        if select_all:
            keys.send("ctrl+a", 0.08)
        keys.send("ctrl+c", 0.02)
        if not clipboard.wait_for_change(seq):
            return ""
        return clipboard.get_text()


def paste_into(hwnd: int, text: str) -> bool:
    """Paste text into a previously focused window (used by the Reply window's Insert)."""
    saved = clipboard.snapshot()
    try:
        if not keys.focus_window(hwnd):
            clipboard.set_text(text)  # leave it on the clipboard so the user can paste
            return False
        clipboard.set_text(text)
        time.sleep(0.05)
        keys.send("ctrl+v", 0.3)
        clipboard.restore(saved)
        return True
    except Exception:
        return False
