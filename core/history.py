"""Last 20 fixes/replies, stored in %APPDATA%\\FixIt\\history.json."""
from __future__ import annotations

import json
import threading
import time

from config import APP_DIR, HISTORY_PATH

MAX_ITEMS = 20
_lock = threading.Lock()


def load() -> list[dict]:
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def add(mode: str, original: str, result: str) -> None:
    with _lock:
        items = load()
        items.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M"), "mode": mode,
                         "original": original, "fixed": result})
        APP_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(items[:MAX_ITEMS], indent=2, ensure_ascii=False), encoding="utf-8")


def clear() -> None:
    with _lock:
        try:
            HISTORY_PATH.unlink()
        except FileNotFoundError:
            pass
