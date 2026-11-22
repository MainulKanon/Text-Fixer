"""Find the focused text box inside web-based desktop apps (WhatsApp Desktop and other WebView2 apps).

Two things hide the box from plain UI Automation (both measured in WhatsApp Desktop, Nov 2026):
  1. The web area's accessibility tree is asleep (2 nodes, no text box) until a client queries it.
  2. Even when awake, the system-wide "focused element" can be the app's outer frame (a Pane),
     never the text box inside.
So: query the web area (which wakes it; the tree is built a moment later), then ask it directly which of
its elements has the keyboard focus.
"""
from __future__ import annotations

import time

import psutil
import win32gui
import win32process

RENDER_CLASS = "Chrome_RenderWidgetHostHWND"   # the web area of any Chromium window
WEBVIEW_EXE = "msedgewebview2.exe"
TREE_DESCENDANTS = 4
SEARCH_EVERY = 0.6      # s between searches while typing …
MAX_QUICK_TRIES = 8     # … and after this many that found nothing in a window …
SLOW_RETRY = 15.0       # … only search it this often (it may simply have no text box)


def _children(hwnd: int) -> list[int]:
    found: list[int] = []

    def cb(h, _):
        try:
            if win32gui.GetClassName(h) == RENDER_CLASS:
                found.append(h)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(hwnd, cb, None)
    except Exception:
        pass
    return found


def render_windows(fg: int) -> list[int]:
    """Web-area windows belonging to the foreground window.

    Usually they're children of it. WhatsApp Desktop instead puts the web area in a separate top-level
    window owned by a WebView2 helper process that the app started, so look there too.
    """
    found = _children(fg)
    if found:
        return found
    try:
        pid = win32process.GetWindowThreadProcessId(fg)[1]
    except Exception:
        return found

    def cb(h, _):
        try:
            if win32gui.IsWindowVisible(h):
                p = psutil.Process(win32process.GetWindowThreadProcessId(h)[1])
                if p.name().lower() == WEBVIEW_EXE and p.ppid() == pid:
                    found.extend(_children(h))
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(cb, None)
    except Exception:
        pass
    return found


class WebBoxFinder:
    """Remembers the focused web text box, because searching a whole page on every poll would be slow."""

    def __init__(self) -> None:
        self._box = None
        self._box_fg = 0
        self._next_search = 0.0
        self._misses: dict[int, int] = {}     # foreground window -> searches in a row that found nothing

    def remembered(self, fg: int):
        """The box found earlier, if it still has the focus. Cheap."""
        if self._box is None:
            return None
        try:
            if fg == self._box_fg and self._box.HasKeyboardFocus:
                return self._box
        except Exception:
            pass
        self._box = None
        return None

    def search(self, auto, fg: int, is_editable):
        """Wake the web area(s) of window `fg` and look for the focused text box. Throttled."""
        now = time.time()
        if now < self._next_search:
            return None
        hosts = render_windows(fg)
        if not hosts:
            self._next_search = now + SEARCH_EVERY
            return None
        for h in hosts:
            try:
                box = self._focused_in(auto, h, is_editable)
            except Exception:
                box = None          # the tree is being (re)built; try again shortly
            if box is not None:
                self._box, self._box_fg = box, fg
                self._misses.pop(fg, None)
                return box
        n = self._misses[fg] = self._misses.get(fg, 0) + 1
        self._next_search = time.time() + (SEARCH_EVERY if n < MAX_QUICK_TRIES else SLOW_RETRY)
        return None

    @staticmethod
    def _focused_in(auto, hwnd: int, is_editable):
        root = auto.ControlFromHandle(hwnd)
        if root is None:
            return None
        # Reading these on the page is what wakes a sleeping tree.
        for c in (root, *root.GetChildren()[:4]):
            c.HasKeyboardFocus
            c.GetPattern(auto.PatternId.ValuePattern)
            c.GetPattern(auto.PatternId.TextPattern)
        uia = auto.uiautomation._AutomationClient.instance().IUIAutomation
        cond = uia.CreatePropertyCondition(auto.PropertyId.HasKeyboardFocusProperty, True)
        hits = root.Element.FindAll(TREE_DESCENDANTS, cond)
        for i in range(hits.Length):
            c = auto.Control.CreateControlFromElement(hits.GetElement(i))
            if c is not None and is_editable(auto, c):
                return c
        return None
