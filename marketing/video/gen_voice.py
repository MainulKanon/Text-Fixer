"""Generates the voiceover clips with ElevenLabs (one mp3 per scene).

Usage (the key is read from the environment and never saved):
  $env:XI_KEY = '<your ElevenLabs key>'
  .venv\\Scripts\\python marketing\\video\\gen_voice.py en
  .venv\\Scripts\\python marketing\\video\\gen_voice.py bn [--voice <voice_id>]

eleven_v3 is the only ElevenLabs model that supports Bangla, so both languages use it for a consistent sound.
Output: marketing\\video\\audio\\<lang>\\1.mp3 … 8.mp3
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
MODEL = "eleven_v3"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"   # "George", an ElevenLabs built-in voice

# How words should be *spoken* (captions keep the written form).
SPOKEN = [("Ctrl+Shift+R", "Control Shift R"), ("Ctrl+Z", "Control Z"), ("FixIt", "Fix-It")]


def spoken(s: str) -> str:
    for a, b in SPOKEN:
        s = s.replace(a, b)
    return s


def main() -> None:
    lang = sys.argv[1]
    voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else DEFAULT_VOICE
    key = os.environ.get("XI_KEY")
    if not key:
        sys.exit("Set XI_KEY first.")
    lines = json.loads((HERE / "voiceover.json").read_text(encoding="utf-8"))[lang]
    out = HERE / "audio" / lang
    out.mkdir(parents=True, exist_ok=True)
    for i, line in enumerate(lines, 1):
        for attempt in range(3):
            r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                           params={"output_format": "mp3_44100_128"},
                           headers={"xi-api-key": key, "Content-Type": "application/json"},
                           json={"text": spoken(line), "model_id": MODEL}, timeout=120)
            if r.status_code == 200:
                (out / f"{i}.mp3").write_bytes(r.content)
                print(f"{lang} {i}/8 ok ({len(r.content) // 1024} KB)")
                break
            print(f"{lang} {i}/8 attempt {attempt + 1} failed: {r.status_code} {r.text[:200]}")
            time.sleep(3)
        else:
            sys.exit(f"Giving up on clip {i}.")


if __name__ == "__main__":
    main()
