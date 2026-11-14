"""Provider registry + fallback chain."""
from __future__ import annotations

import re

from .base import ModelNotFound, Provider, ProviderError
from .gemini import GeminiProvider
from .openai_compat import GroqProvider, OpenRouterProvider

PROVIDERS: dict[str, Provider] = {p.name: p for p in (GroqProvider(), GeminiProvider(), OpenRouterProvider())}


def clean_output(text: str) -> str:
    """Strip markdown fences, 'Here is...' preambles and surrounding quotes."""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", t).strip()
    t = re.sub(r"^(here(?:'s| is) (?:the |your )?(?:fixed|corrected|rewritten|improved)[^:\n]*:)\s*", "", t, flags=re.I).strip()
    pairs = [('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"), ("«", "»")]
    for _ in range(2):
        for a, b in pairs:
            if len(t) >= 2 and t.startswith(a) and t.endswith(b) and t.count(a) <= 2:
                t = t[len(a):-len(b)].strip()
    return t


def complete_with_model_fallback(prov: Provider, key: str, model: str, system: str, user: str) -> tuple[str, str]:
    """Call the provider; if the model was retired / doesn't exist, pick an available one and retry.
    Returns (raw_text, model_used)."""
    try:
        if not model:
            raise ModelNotFound(f"{prov.label}: no model set")
        return prov.complete(key, model, system, user), model
    except ModelNotFound as first:
        models = prov.list_models(key)
        candidates = [m for m in models if m != model]
        new = prov.pick_model(candidates)
        if not new:
            raise ProviderError(f"{first} – and no replacement model was found") from first
        return prov.complete(key, new, system, user), new


def run_chain(cfg, system: str, user: str) -> tuple[str, str]:
    """Try providers in configured order (only those with a key). Returns (text, provider_label)."""
    order = cfg.get("provider_order") or list(PROVIDERS)
    settings = cfg.get("providers", {})
    errors = []
    tried = 0
    for name in order:
        prov = PROVIDERS.get(name)
        s = settings.get(name, {})
        key = (s.get("api_key") or "").strip()
        if not prov or not key:
            continue
        tried += 1
        try:
            raw, used = complete_with_model_fallback(prov, key, (s.get("model") or "").strip(), system, user)
            if used != s.get("model") and hasattr(cfg, "save"):
                s["model"] = used  # remember the working model
                cfg.save()
            out = clean_output(raw)
            if out:
                return out, prov.label
            errors.append(f"{prov.label}: empty response")
        except ProviderError as e:
            errors.append(str(e))
    if not tried:
        raise ProviderError("No API key set. Right-click the tray icon → Settings and add a Groq key.")
    raise ProviderError(" | ".join(errors))


__all__ = ["PROVIDERS", "Provider", "ProviderError", "ModelNotFound", "run_chain", "clean_output",
           "complete_with_model_fallback"]
