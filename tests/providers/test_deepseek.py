# test_deepseek.py
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
from proxy.providers.deepseek_provider import DeepSeekProvider


async def test():
    provider = DeepSeekProvider()
    response = await provider.complete(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "Say exactly: 'Hello from DeepSeek'"}
        ],
        max_tokens=50,
        temperature=0.0
    )
    print(f"Content: {response.content}")
    print(f"Tokens: {response.prompt_tokens}p + {response.completion_tokens}c")
    print(f"Model: {response.model}")
    print(f"Finish: {response.finish_reason}")


asyncio.run(test())
