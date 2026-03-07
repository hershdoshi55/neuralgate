# test_router.py
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from proxy.classifier import classify_complexity
from proxy.router import select_model
from proxy.model_registry import MODEL_REGISTRY

test_prompts = [
    ("What is 2+2?", "auto", None, None),
    ("Analyze the geopolitical implications of AI development", "auto", None, None),
    ("Write a poem", "cheapest", None, None),
    ("Complex analysis needed", "best", None, None),
    ("Quick question", "auto", "anthropic", None),    # Force anthropic provider
    ("Small budget question", "auto", None, 0.0001),  # Cost cap: $0.0001
]

print("Router Test Results:")
for prompt, requested_model, preferred_provider, max_cost in test_prompts:
    messages = [{"role": "user", "content": prompt}]
    complexity = classify_complexity(messages)
    selected, failover = select_model(
        requested_model=requested_model,
        complexity_result=complexity,
        prompt_tokens=complexity["total_tokens"],
        preferred_provider=preferred_provider,
        max_cost_per_request=max_cost,
    )
    info = MODEL_REGISTRY[selected]
    print(f"Prompt: {prompt[:40]!r}")
    print(f"  Requested: {requested_model} | Complexity: {complexity['tier']} ({complexity['score']:.2f})")
    print(f"  Selected: {selected} ({info['provider']}) | Tier: {info['tier']} | ${info['input_cost_per_million']}/M in")
    print(f"  Failover: {failover[:2]}")
    print()
