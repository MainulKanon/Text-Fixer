"""Clipboard helpers: snapshot/restore, read/write text, wait for copy."""
from __future__ import annotations

import time

import win32clipboard as wcb
import win32con

# Formats we can safely snapshot as raw bytes (handle-based formats like CF_BITMAP are skipped;
# CF_DIB covers images).
_SAFE_STD = {win32con.CF_UNICODETEXT, win32con.CF_TEXT, win32con.CF_DIB, win32con.CF_DIBV5, win32con.CF_LOCALE}


def _open(retries: int = 20) -> None:
    for _ in range(retries):
        try:
            wcb.OpenClipboard()
            return
        except Exception:
            time.sleep(0.03)
    wcb.OpenClipboard()  # final attempt raises the real error


def sequence() -> int:
    return wcb.GetClipboardSequenceNumber()


def snapshot() -> list[tuple[int, object]]:
    saved = []
    try:
        _open()
    except Exception:
        return saved
    try:
        fmt = 0
        while True:
            fmt = wcb.EnumClipboardFormats(fmt)
            if not fmt:
                break
            if fmt in _SAFE_STD or fmt >= 0xC000:
                try:
                    saved.append((fmt, wcb.GetClipboardData(fmt)))
                except Exception:
                    pass
    finally:
        wcb.CloseClipboard()
    return saved


def restore(saved: list[tuple[int, object]]) -> None:
    try:
        _open()
    except Exception:
        return
    try:
        wcb.EmptyClipboard()
        for fmt, data in saved:
            try:
                if fmt == win32con.CF_UNICODETEXT and isinstance(data, str):
                    wcb.SetClipboardText(data, fmt)
                else:
                    wcb.SetClipboardData(fmt, data)
            except Exception:
                pass
    finally:
        wcb.CloseClipboard()


def clear() -> None:
    try:
        _open()
        try:
            wcb.EmptyClipboard()
        finally:
            wcb.CloseClipboard()
    except Exception:
        pass


def get_text() -> str:
    try:
        _open()
    except Exception:
        return ""
    try:
        if wcb.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return wcb.GetClipboardData(win32con.CF_UNICODETEXT) or ""
        return ""
    except Exception:
        return ""
    finally:
        wcb.CloseClipboard()


def set_text(text: str) -> None:
    _open()
    try:
        wcb.EmptyClipboard()
        wcb.SetClipboardText(text, win32con.CF_UNICODETEXT)
    finally:
        wcb.CloseClipboard()


def wait_for_change(old_seq: int, timeout: float = 1.5) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if sequence() != old_seq:
            time.sleep(0.05)  # let the app finish writing all formats
            return True
        time.sleep(0.02)
    return False
