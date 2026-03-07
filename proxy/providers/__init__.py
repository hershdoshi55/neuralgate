from proxy.providers.anthropic_provider import AnthropicProvider
from proxy.providers.openai_provider import OpenAIProvider
from proxy.providers.google_provider import GoogleProvider
from proxy.providers.deepseek_provider import DeepSeekProvider
from proxy.providers.xai_provider import XAIProvider
from proxy.providers.mistral_provider import MistralProvider
from proxy.settings import settings, get_available_providers

# Lazy instantiation — only create providers where we have API keys
_providers = {}


def get_provider(provider_name: str):
    if provider_name not in _providers:
        available = get_available_providers()
        if provider_name not in available:
            raise ValueError(f"Provider '{provider_name}' not configured. Add API key to .env")

        if provider_name == "anthropic":
            _providers[provider_name] = AnthropicProvider()
        elif provider_name == "openai":
            _providers[provider_name] = OpenAIProvider()
        elif provider_name == "google":
            _providers[provider_name] = GoogleProvider()
        elif provider_name == "deepseek":
            _providers[provider_name] = DeepSeekProvider()
        elif provider_name == "xai":
            _providers[provider_name] = XAIProvider()
        elif provider_name == "mistral":
            _providers[provider_name] = MistralProvider()

    return _providers[provider_name]
