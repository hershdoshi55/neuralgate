# test_openai.py
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
from proxy.providers.openai_provider import OpenAIProvider


async def test():
    provider = OpenAIProvider()
    response = await provider.complete(
        model="gpt-5-nano",
        messages=[
            {"role": "user", "content": "Say exactly: 'Hello from OpenAI'"}
        ],
        max_tokens=500,
        temperature=0.0
    )
    print(f"Content: {response.content}")
    print(f"Tokens: {response.prompt_tokens}p + {response.completion_tokens}c")
    print(f"Model: {response.model}")
    print(f"Finish: {response.finish_reason}")


asyncio.run(test())
