import re

import httpx

from .base import Provider, ProviderError

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Thinking levels to try, fastest first. Big "flash" models take 15-30 s with default thinking, which is
# far too slow for a grammar fix; "minimal" brings gemini-3.5-flash down to ~2.5 s.
THINKING_LEVELS = ("minimal", "low", None)


def _version_key(m: str):
    v = re.search(r"gemini-(\d+(?:\.\d+)?)", m)
    return -float(v.group(1)) if v else 0


class GeminiProvider(Provider):
    name = "gemini"
    label = "Gemini"
    key_url = "https://aistudio.google.com/app/apikey"
    timeout = 25.0
    # Measured Nov 2026: fast + good quality first. Newest big flash models (3.7/3.8) are slow, so they come last.
    preferred_models = ("gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.5-flash-lite",
                        "gemini-3.1-flash-lite", "flash-lite", "flash")
    excluded_model_words = Provider.excluded_model_words + (
        "pro", "omni", "robotics", "computer-use", "customtools", "nano", "argon", "exp", "preview")

    def __init__(self) -> None:
        self._level_for: dict[str, str | None] = {}   # model -> thinking level that worked

    def _post(self, api_key: str, model: str, body: dict) -> httpx.Response:
        try:
            # Key in a header, not in the URL.
            return httpx.post(f"{BASE}/models/{model}:generateContent", headers={"x-goog-api-key": api_key},
                              json=body, timeout=self.timeout)
        except httpx.TimeoutException as e:
            raise ProviderError(f"{self.label}: {model} took longer than {int(self.timeout)} s – "
                                f"pick a faster model (e.g. gemini-3.5-flash)") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: network error ({e})") from e

    def complete(self, api_key: str, model: str, system: str, user: str) -> str:
        model = model.removeprefix("models/")
        levels = [self._level_for[model]] if model in self._level_for else list(THINKING_LEVELS)
        resp = None
        for level in levels:
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.3},
            }
            if level:
                body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": level}
            resp = self._post(api_key, model, body)
            if resp.status_code == 400 and "thinking" in resp.text.lower():
                continue  # this model doesn't support that thinking level; try the next one
            self._level_for[model] = level
            break
        self._raise_for(resp, self.label)
        try:
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except Exception as e:
            raise ProviderError(f"{self.label}: empty or blocked response") from e

    def list_models(self, api_key: str) -> list[str]:
        try:
            resp = httpx.get(f"{BASE}/models", headers={"x-goog-api-key": api_key},
                             params={"pageSize": 200}, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: network error ({e})") from e
        self._raise_for(resp, self.label)
        out = []
        for m in resp.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                mid = m.get("name", "").removeprefix("models/")
                if mid.startswith("gemini"):
                    out.append(mid)
        return sorted(out, key=lambda m: (_version_key(m), m))  # newest first
