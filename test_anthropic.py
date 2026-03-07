# test_anthropic.py
import asyncio
from proxy.providers.anthropic_provider import AnthropicProvider


async def test():
    provider = AnthropicProvider()
    response = await provider.complete(
        model="claude-haiku-4-5-20251001",  # Use cheapest for testing
        messages=[
            {"role": "user", "content": "Say exactly: 'Hello from Anthropic'"}
        ],
        max_tokens=50,
        temperature=0.0
    )
    print(f"Content: {response.content}")
    print(f"Tokens: {response.prompt_tokens}p + {response.completion_tokens}c")
    print(f"Model: {response.model}")
    print(f"Finish: {response.finish_reason}")


asyncio.run(test())
