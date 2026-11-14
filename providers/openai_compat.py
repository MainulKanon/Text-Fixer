from .base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    label = "Groq"
    key_url = "https://console.groq.com/keys"
    url = "https://api.groq.com/openai/v1/chat/completions"
    models_url = "https://api.groq.com/openai/v1/models"
    preferred_models = ("gpt-oss-120b", "llama-3.3-70b", "llama-4-maverick", "llama-4", "kimi-k2",
                        "qwen3", "gpt-oss-20b", "70b", "versatile", "llama-3.1-8b", "instant")
    excluded_model_words = OpenAICompatibleProvider.excluded_model_words + ("compound", "allam", "safeguard")

    def _body(self, model, system, user):
        body = super()._body(model, system, user)
        if "gpt-oss" in model or "qwen3" in model:
            body["reasoning_effort"] = "low"  # much faster for simple rewrites
        return body


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    label = "OpenRouter"
    key_url = "https://openrouter.ai/keys"
    url = "https://openrouter.ai/api/v1/chat/completions"
    models_url = "https://openrouter.ai/api/v1/models"
    extra_headers = {"X-Title": "Text Fixer"}
    preferred_models = ("gpt-oss-120b:free", "llama-3.3-70b-instruct:free", "llama-4-maverick:free",
                        "deepseek-chat", "gemini", "qwen3", "mistral-small", "70b")

    def list_models(self, api_key: str) -> list[str]:
        # Only free models.
        return [m for m in super().list_models(api_key) if m.endswith(":free")]

    def pick_model(self, models: list[str]) -> str | None:
        return super().pick_model([m for m in models if m.endswith(":free")])
