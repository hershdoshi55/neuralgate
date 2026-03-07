import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings


class AnthropicProvider(BaseProvider):
    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0
        )

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """
        OpenAI format → Anthropic format.

        Key differences:
        1. System prompt is a top-level "system" field, not in messages array
        2. Anthropic doesn't use "system" role in messages array
        3. max_tokens is required in Anthropic (optional in OpenAI)
        """
        system = None
        filtered_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        request = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens or 4096,
        }

        if system:
            request["system"] = system

        if temperature is not None:
            request["temperature"] = temperature

        return request

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        Anthropic response structure:
        {
            "content": [{"type": "text", "text": "..."}],
            "model": "claude-haiku-4-5-20251001",
            "usage": {"input_tokens": 24, "output_tokens": 9},
            "stop_reason": "end_turn"
        }
        """
        content = ""
        for block in raw.get("content", []):
            if block.get("type") == "text":
                content += block["text"]

        usage = raw.get("usage", {})

        stop_reason_map = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
        }

        return ProviderResponse(
            content=content,
            model=raw.get("model", "unknown"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            finish_reason=stop_reason_map.get(raw.get("stop_reason", "end_turn"), "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        response = await self.client.post("/messages", json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
