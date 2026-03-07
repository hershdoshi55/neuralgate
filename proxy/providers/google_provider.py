import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings


class GoogleProvider(BaseProvider):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.api_key = settings.google_api_key

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """
        OpenAI format → Google Gemini format.

        Key differences:
        1. Messages go in "contents" not "messages"
        2. Content is in "parts" array: [{"text": "..."}]
        3. System prompt goes in "systemInstruction"
        4. Generation config is separate: {"generationConfig": {...}}
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                # Map "assistant" → "model" for Gemini
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        request = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens or 4096,
                "temperature": temperature,
            }
        }

        if system_instruction:
            request["systemInstruction"] = system_instruction

        return request

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        Google response structure:
        {
            "candidates": [{"content": {"parts": [{"text": "..."}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 24, "candidatesTokenCount": 9}
        }
        """
        candidate = raw["candidates"][0]
        content = ""
        for part in candidate["content"]["parts"]:
            content += part.get("text", "")

        usage = raw.get("usageMetadata", {})
        finish_map = {"STOP": "stop", "MAX_TOKENS": "length"}

        return ProviderResponse(
            content=content,
            model="gemini",
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=finish_map.get(candidate.get("finishReason", "STOP"), "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        # Google uses the model name in the URL, not the request body
        url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"
        response = await self.client.post(url, json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
