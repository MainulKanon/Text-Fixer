"""Configuration stored in %APPDATA%\\FixIt\\config.json."""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path

APP_NAME = "FixIt"
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_PATH = APP_DIR / "config.json"
HISTORY_PATH = APP_DIR / "history.json"

DEFAULT_SYSTEM_PROMPT = (
    "Fix grammar and make this sound natural and professional for a client. "
    "Keep my meaning and tone. Return only the fixed text."
)

# Always appended to every rewrite prompt.
OUTPUT_RULES = (
    "Rules: Do not add greetings, sign-offs, quotes, explanations, or markdown. "
    "Keep the same language as the input (unless asked to translate). "
    "Keep emojis, names, links and numbers unchanged. "
    "Output only the final text, nothing else."
)

DEFAULT_MODES = {
    "Fix grammar": DEFAULT_SYSTEM_PROMPT,
    "More professional": (
        "Rewrite this to sound more polished and professional for a client, "
        "keeping my meaning. Return only the rewritten text."
    ),
    "Shorter": (
        "Make this shorter and more concise while keeping the key meaning and "
        "a natural, professional tone. Return only the rewritten text."
    ),
    "Friendlier": (
        "Rewrite this to sound warmer and friendlier while staying professional. "
        "Keep my meaning. Return only the rewritten text."
    ),
    "Translate Bangla → English": (
        "Translate this text from Bangla (it may be written in Bangla script or "
        "romanized Banglish) into natural, professional English. "
        "Return only the English translation."
    ),
}

DEFAULT_REPLY_PROMPT = (
    "You are helping me reply to a message I received (from a client, email, chat, etc.). "
    "Write a reply I can send, in first person, that is natural, clear and professional. "
    "Answer every question or point in the message. Do not invent facts, prices, dates or "
    "promises; if information is missing, use a short placeholder like [date]. "
    "Reply in the same language as the message. Return only the reply text, no subject "
    "line, no quotes, no markdown, no explanations."
)

REPLY_TONES = ["Professional", "Friendly", "Short", "Detailed", "Polite decline"]

PROVIDER_DEFAULTS = {
    # If a model gets retired, Text Fixer automatically picks an available one and saves it.
    "groq": {"api_key": "", "model": "openai/gpt-oss-120b"},
    "gemini": {"api_key": "", "model": "gemini-3.5-flash"},
    "openrouter": {"api_key": "", "model": "openai/gpt-oss-120b:free"},
}

DEFAULTS = {
    "providers": PROVIDER_DEFAULTS,
    "provider_order": ["groq", "gemini", "openrouter"],
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "modes": DEFAULT_MODES,
    "reply_prompt": DEFAULT_REPLY_PROMPT,
    "show_button": True,
    "preview_before_replace": True,
    "hotkey": "ctrl+shift+g",
    "reply_hotkey": "ctrl+shift+r",
    "min_chars": 5,
    "idle_delay": 1.0,
    "hide_after": 10.0,
    "excluded_apps": [
        "code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe",
        "notepad++.exe", "windowsterminal.exe", "cmd.exe", "powershell.exe",
        "keepass.exe", "keepassxc.exe", "1password.exe", "bitwarden.exe",
    ],
    "start_with_windows": False,
    "paused": False,
}


def _merge(defaults: dict, data: dict) -> dict:
    out = copy.deepcopy(defaults)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.data: dict = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self) -> None:
        with self._lock:
            try:
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.data = _merge(DEFAULTS, raw)
            except FileNotFoundError:
                self.save()
            except Exception:
                # Corrupt config: keep a backup and start fresh.
                try:
                    CONFIG_PATH.replace(CONFIG_PATH.with_suffix(".bad.json"))
                except OSError:
                    pass
                self.data = copy.deepcopy(DEFAULTS)
                self.save()

    def save(self) -> None:
        with self._lock:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CONFIG_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(CONFIG_PATH)

    def get(self, key, default=None):
        with self._lock:
            return self.data.get(key, default)

    def set(self, key, value) -> None:
        with self._lock:
            self.data[key] = value
            self.save()

    def prompt_for_mode(self, mode: str) -> str:
        if mode == "Fix grammar":
            base = self.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
        else:
            base = self.get("modes", {}).get(mode) or DEFAULT_MODES.get(mode, DEFAULT_SYSTEM_PROMPT)
        return f"{base}\n\n{OUTPUT_RULES}"

    def mode_names(self) -> list[str]:
        names = list(self.get("modes", {}).keys())
        if "Fix grammar" not in names:
            names.insert(0, "Fix grammar")
        return names


config = Config()
