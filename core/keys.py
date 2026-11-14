"""Sending keystrokes to the focused window."""
from __future__ import annotations

import time

import keyboard
import win32api
import win32con
import win32gui
import win32process

MODIFIERS = ("ctrl", "shift", "alt", "left windows", "right windows")

# Set while FixIt is injecting keys, so the focus watcher can ignore them.
injecting = False


def wait_modifiers_released(timeout: float = 2.0) -> None:
    """After a hotkey, the user may still be holding Ctrl/Shift; wait so Ctrl+A isn't Ctrl+Shift+A."""
    end = time.time() + timeout
    while time.time() < end:
        if not any(keyboard.is_pressed(m) for m in MODIFIERS):
            return
        time.sleep(0.02)
    for m in MODIFIERS:
        try:
            keyboard.release(m)
        except Exception:
            pass


def send(combo: str, delay: float = 0.06) -> None:
    global injecting
    injecting = True
    try:
        keyboard.send(combo)
        time.sleep(delay)
    finally:
        injecting = False


def foreground() -> int:
    return win32gui.GetForegroundWindow()


def focus_window(hwnd: int) -> bool:
    """Bring hwnd back to the foreground (works around SetForegroundWindow restrictions)."""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    if win32gui.GetForegroundWindow() == hwnd:
        return True
    try:
        fg = win32gui.GetForegroundWindow()
        cur = win32api.GetCurrentThreadId()
        fg_thread = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
        target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
        # A harmless Alt tap lets us take the foreground.
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        for t in {fg_thread, target_thread} - {0, cur}:
            win32process.AttachThreadInput(cur, t, True)
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            for t in {fg_thread, target_thread} - {0, cur}:
                win32process.AttachThreadInput(cur, t, False)
    except Exception:
        pass
    time.sleep(0.15)
    return win32gui.GetForegroundWindow() == hwnd
