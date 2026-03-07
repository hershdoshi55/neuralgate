import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings


class OpenAIProvider(BaseProvider):
    BASE_URL = "https://api.openai.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0
        )

    # Reasoning models don't support custom temperature
    REASONING_MODELS = {"gpt-5-nano", "gpt-5-mini", "gpt-5.4", "o1", "o3", "o3-mini", "o1-mini", "o1-preview"}

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """OpenAI → OpenAI: no translation needed."""
        body = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_tokens or 4096,
        }
        # Reasoning models only support default temperature (1)
        base_model = model.split("-20")[0]  # strip date suffix e.g. gpt-5-nano-2025-08-07
        if base_model not in self.REASONING_MODELS:
            body["temperature"] = temperature
        return body

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        OpenAI response structure:
        {
            "choices": [{"message": {"content": "..."}, "finish_reason": "stop"}],
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 24, "completion_tokens": 9}
        }
        """
        choice = raw["choices"][0]
        usage = raw.get("usage", {})

        return ProviderResponse(
            content=choice["message"]["content"],
            model=raw.get("model", "unknown"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        response = await self.client.post("/chat/completions", json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
