from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    """Normalized response — same structure regardless of which provider ran."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    raw_response: dict  # Original provider response, stored for debugging


class BaseProvider(ABC):
    """Every provider adapter implements this interface."""

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> ProviderResponse:
        """Send chat completion request, return normalized response."""
        pass

    @abstractmethod
    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """Convert OpenAI-format messages to provider-specific format."""
        pass

    @abstractmethod
    def parse_response(self, raw: dict) -> ProviderResponse:
        """Convert provider response to normalized ProviderResponse."""
        pass
