"""Provider interface. To add a provider: subclass Provider, then register it in providers/__init__.py."""
from __future__ import annotations

import httpx


class ProviderError(Exception):
    """Raised when a provider call fails (network, auth, rate limit, bad response)."""


class ModelNotFound(ProviderError):
    """The configured model doesn't exist / was retired. Callers can pick another via list_models()."""


_MODEL_GONE_HINTS = ("does not exist", "not found", "decommission", "deprecated", "no longer supported",
                     "not supported", "do not have access", "no endpoints found", "is not a valid model")


class Provider:
    name: str = "base"
    label: str = "Base"
    key_url: str = ""
    timeout = 30.0
    # Substrings tried in order when picking a replacement model.
    preferred_models: tuple[str, ...] = ()
    # Models containing any of these are never picked (audio, embeddings, safety classifiers…).
    excluded_model_words: tuple[str, ...] = ("whisper", "tts", "guard", "embed", "audio", "image", "vision-only",
                                             "transcribe", "speech", "moderation", "playai", "orpheus", "prompt-guard")

    def complete(self, api_key: str, model: str, system: str, user: str) -> str:
        raise NotImplementedError

    def list_models(self, api_key: str) -> list[str]:
        """Chat-capable model ids available to this key."""
        return []

    def pick_model(self, models: list[str]) -> str | None:
        usable = [m for m in models if not any(w in m.lower() for w in self.excluded_model_words)]
        for pref in self.preferred_models:
            for m in usable:
                if pref in m.lower():
                    return m
        return usable[0] if usable else None

    @staticmethod
    def _raise_for(resp: httpx.Response, label: str) -> None:
        if resp.status_code < 400:
            return
        try:
            j = resp.json()
            err = j.get("error", j) if isinstance(j, dict) else j
            if isinstance(err, list) and err:
                err = err[0].get("error", err[0]) if isinstance(err[0], dict) else err[0]
            msg = err.get("message") if isinstance(err, dict) else str(err)
        except Exception:
            msg = resp.text[:200]
        msg = msg or resp.reason_phrase
        low = msg.lower()
        if resp.status_code == 429:
            raise ProviderError(f"{label}: rate limit reached ({msg})")
        if resp.status_code in (401, 403) and "model" not in low:
            raise ProviderError(f"{label}: invalid API key ({msg})")
        if resp.status_code in (400, 403, 404) and "model" in low and any(h in low for h in _MODEL_GONE_HINTS):
            raise ModelNotFound(f"{label}: model unavailable ({msg})")
        if resp.status_code == 404:
            raise ModelNotFound(f"{label}: model unavailable ({msg})")
        raise ProviderError(f"{label}: HTTP {resp.status_code} – {msg}")


class OpenAICompatibleProvider(Provider):
    url: str = ""            # .../chat/completions
    models_url: str = ""     # .../models
    extra_headers: dict = {}

    def _headers(self, api_key: str) -> dict:
        h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        h.update(self.extra_headers)
        return h

    def _body(self, model: str, system: str, user: str) -> dict:
        return {
            "model": model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def complete(self, api_key: str, model: str, system: str, user: str) -> str:
        body = self._body(model, system, user)
        try:
            resp = httpx.post(self.url, headers=self._headers(api_key), json=body, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: network error ({e})") from e
        self._raise_for(resp, self.label)
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except Exception as e:
            raise ProviderError(f"{self.label}: unexpected response") from e

    def list_models(self, api_key: str) -> list[str]:
        try:
            resp = httpx.get(self.models_url, headers=self._headers(api_key), timeout=self.timeout)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.label}: network error ({e})") from e
        self._raise_for(resp, self.label)
        data = resp.json().get("data", [])
        return sorted(m["id"] for m in data if m.get("id") and m.get("active", True) is not False)
