# test_google.py
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
from proxy.providers.google_provider import GoogleProvider


async def test():
    provider = GoogleProvider()
    response = await provider.complete(
        model="gemini-2.5-flash-lite",  # Use cheapest for testing
        messages=[
            {"role": "user", "content": "Say exactly: 'Hello from Google'"}
        ],
        max_tokens=500,
        temperature=0.0
    )
    print(f"Content: {response.content}")
    print(f"Tokens: {response.prompt_tokens}p + {response.completion_tokens}c")
    print(f"Model: {response.model}")
    print(f"Finish: {response.finish_reason}")


asyncio.run(test())
