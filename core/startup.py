"""Start with Windows via HKCU\\...\\Run."""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "TextFixer"
LEGACY_VALUES = ("FixIt",)   # the app's old name


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    main = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{exe}" "{main}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            for name in (VALUE, *LEGACY_VALUES):
                try:
                    winreg.QueryValueEx(k, name)
                    return True
                except OSError:
                    pass
    except OSError:
        pass
    return False


def set_enabled(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        for name in LEGACY_VALUES:          # never leave the old entry behind
            try:
                winreg.DeleteValue(k, name)
            except FileNotFoundError:
                pass
        if enabled:
            winreg.SetValueEx(k, VALUE, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(k, VALUE)
            except FileNotFoundError:
                pass
