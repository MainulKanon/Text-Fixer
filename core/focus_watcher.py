"""Watches the focused UI element (via Windows UI Automation) and decides when the ✨ button shows.

Runs in its own thread. Emits:
  show_request(dict)  – {"field": (l,t,r,b) | None, "caret": (l,t,r,b) | None, "mouse": (x,y), "hwnd": int}
  hide_request()
All coordinates are physical screen pixels.
"""
from __future__ import annotations

import threading
import time

import keyboard
import psutil
import win32api
import win32gui
from PySide6.QtCore import QObject, Signal

from config import config

from . import keys

POLL = 0.2


class FocusWatcher(QObject):
    show_request = Signal(dict)
    hide_request = Signal()

    def __init__(self, fixer) -> None:
        super().__init__()
        self.fixer = fixer
        self.hover = False            # set by the button while the mouse is over it
        self._stop = threading.Event()
        self._last_key = 0.0
        self._pid_names: dict[int, str] = {}
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        keyboard.hook(self._on_key)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _on_key(self, ev) -> None:
        if ev.event_type == "down" and not keys.injecting and not self.fixer.busy:
            self._last_key = time.time()

    # ---------- UIA helpers ----------
    def _proc_name(self, pid: int) -> str:
        name = self._pid_names.get(pid)
        if name is None:
            try:
                name = psutil.Process(pid).name().lower()
            except Exception:
                name = ""
            self._pid_names[pid] = name
        return name

    @staticmethod
    def _is_editable(auto, ctrl) -> bool:
        try:
            if not ctrl.IsEnabled or not ctrl.IsKeyboardFocusable:
                return False
            if getattr(ctrl, "IsPassword", False):
                return False
            ct = ctrl.ControlType
            vp = ctrl.GetPattern(auto.PatternId.ValuePattern)
            readonly = bool(vp.IsReadOnly) if vp else None
            if ct == auto.ControlType.EditControl:
                return readonly is not True
            if ct == auto.ControlType.DocumentControl:
                return readonly is False
            # Some rich editors expose other types but a writable Value
            return readonly is False and ct in (auto.ControlType.ComboBoxControl, auto.ControlType.CustomControl,
                                                auto.ControlType.GroupControl, auto.ControlType.PaneControl)
        except Exception:
            return False

    @staticmethod
    def _text_len(auto, ctrl, limit: int) -> int:
        try:
            vp = ctrl.GetPattern(auto.PatternId.ValuePattern)
            if vp:
                v = vp.Value or ""
                if v.strip():
                    return len(v.strip())
        except Exception:
            pass
        try:
            tp = ctrl.GetPattern(auto.PatternId.TextPattern)
            if tp:
                return len((tp.DocumentRange.GetText(limit + 50) or "").strip())
        except Exception:
            pass
        return limit  # unknown → assume enough so the user can still use the button

    @staticmethod
    def _rect(r):
        try:
            t = (int(r.left), int(r.top), int(r.right), int(r.bottom))
            return t if t[2] > t[0] and t[3] > t[1] else None
        except Exception:
            return None

    def _caret(self, auto, ctrl):
        try:
            tp = ctrl.GetPattern(auto.PatternId.TextPattern)
            if not tp:
                return None
            sel = tp.GetSelection()
            if not sel:
                return None
            rng = sel[0]
            rects = rng.GetBoundingRectangles()
            if not rects:
                # Degenerate (empty) range: expand to one character to get a rect.
                rng = rng.Clone()
                rng.ExpandToEnclosingUnit(auto.TextUnit.Character)
                rects = rng.GetBoundingRectangles()
            if rects:
                return self._rect(rects[-1])
        except Exception:
            pass
        return None

    @staticmethod
    def _runtime_id(ctrl):
        try:
            return tuple(ctrl.GetRuntimeId())
        except Exception:
            try:
                return (ctrl.NativeWindowHandle, ctrl.ControlType, ctrl.Name)
            except Exception:
                return None

    # ---------- main loop ----------
    def _run(self) -> None:
        import uiautomation as auto

        auto.SetGlobalSearchTimeout(1)
        with auto.UIAutomationInitializerInThread():
            current = None
            focus_key_time = 0.0   # last-key time when focus entered this element
            shown_for = 0.0         # last-key time for which we positioned the button
            shown = False

            def hide():
                nonlocal shown
                if shown:
                    shown = False
                    self.hide_request.emit()

            while not self._stop.is_set():
                time.sleep(POLL)
                try:
                    if self.fixer.busy:
                        continue  # keep the button (spinner) where it is
                    if config.get("paused") or not config.get("show_button", True):
                        hide()
                        continue

                    ctrl = auto.GetFocusedControl()
                    if ctrl is None or not self._is_editable(auto, ctrl):
                        if not self.hover:
                            hide()
                            current = None
                        continue

                    excluded = {a.strip().lower() for a in config.get("excluded_apps", []) if a.strip()}
                    if self._proc_name(ctrl.ProcessId) in excluded:
                        hide()
                        continue

                    rid = self._runtime_id(ctrl)
                    if rid != current:
                        hide()
                        current = rid
                        focus_key_time = self._last_key
                        shown_for = 0.0

                    last = self._last_key
                    if last <= focus_key_time:
                        continue  # no typing in this field yet
                    idle = time.time() - last

                    if shown and idle >= float(config.get("hide_after", 10)) and not self.hover:
                        hide()
                        shown_for = last  # don't re-show until the user types again
                        continue

                    if idle >= float(config.get("idle_delay", 1.0)) and shown_for != last:
                        shown_for = last
                        min_chars = int(config.get("min_chars", 5))
                        if self._text_len(auto, ctrl, min_chars) < min_chars:
                            hide()
                            continue
                        field = self._rect(ctrl.BoundingRectangle)
                        caret = self._caret(auto, ctrl)
                        self.show_request.emit({
                            "field": field,
                            "caret": caret,
                            "mouse": win32api.GetCursorPos(),
                            "hwnd": win32gui.GetForegroundWindow(),
                        })
                        shown = True
                except Exception:
                    # UIA calls can fail when windows close mid-query; just try again next tick.
                    current = None
                    time.sleep(0.3)
