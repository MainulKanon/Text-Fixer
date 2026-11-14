"""Win32 helpers to make Qt windows non-activating overlays."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui

WM_MOUSEACTIVATE = 0x0021
MA_NOACTIVATE = 3


def make_non_activating(widget) -> int:
    hwnd = int(widget.winId())
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex |= win32con.WS_EX_NOACTIVATE | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST
    ex &= ~win32con.WS_EX_APPWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
    return hwnd


def is_mouse_activate(message) -> bool:
    try:
        msg = wintypes.MSG.from_address(int(message))
        return msg.message == WM_MOUSEACTIVATE
    except Exception:
        return False


def move_physical(hwnd: int, x: int, y: int) -> None:
    """Move to physical pixel coords and show, without activating."""
    flags = win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, int(x), int(y), 0, 0, flags)


def window_size(hwnd: int) -> tuple[int, int]:
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return r - l, b - t


def work_area(x: int, y: int) -> tuple[int, int, int, int]:
    try:
        mon = win32api.MonitorFromPoint((int(x), int(y)), win32con.MONITOR_DEFAULTTONEAREST)
        return win32api.GetMonitorInfo(mon)["Work"]
    except Exception:
        return 0, 0, ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
