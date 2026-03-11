"""
Step 4.6 — Test NeuralGate proxy with the real OpenAI Python SDK.
Run from repo root: python tests/test_sdk.py
The proxy must be running at http://localhost:8000
"""
import os
from openai import OpenAI

PROXY_URL = "http://localhost:8000/v1"
API_KEY = os.getenv("PROXY_API_KEY", "test-key")  # set PROXY_API_KEY if auth is enabled

client = OpenAI(base_url=PROXY_URL, api_key=API_KEY)


def chat(model: str, prompt: str) -> None:
    print(f"\n{'='*60}")
    print(f"model={model!r}")
    print(f"prompt={prompt!r}")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    msg = resp.choices[0].message.content
    actual_model = resp.model
    print(f"actual_model={actual_model!r}")
    print(f"response={msg[:200]!r}")


def list_models() -> None:
    print(f"\n{'='*60}")
    print("GET /v1/models")
    models = client.models.list()
    virtual = {"auto", "cheapest", "balanced", "best"}
    virtual_found = []
    for m in models.data:
        if m.id in virtual:
            virtual_found.append(m.id)
    print(f"Virtual aliases found: {virtual_found}")
    print(f"Total models: {len(models.data)}")
    # Print first 8 model IDs
    for m in models.data[:8]:
        print(f"  {m.id}")


if __name__ == "__main__":
    # 1. List models — virtual aliases should appear at the top
    list_models()

    # 2. Simple question → should route to cheap tier
    chat("auto", "What is 2 + 2?")

    # 3. Complex question → should route to frontier tier
    chat(
        "auto",
        "Write a detailed technical analysis of the trade-offs between "
        "transformer attention mechanisms and state-space models (SSMs) for "
        "long-context language modeling, including mathematical derivations.",
    )

    # 4. Explicit alias → frontier
    chat("best", "Hello!")

    print(f"\n{'='*60}")
    print("All tests passed.")
