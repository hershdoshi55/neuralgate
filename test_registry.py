# test_registry.py
from proxy.model_registry import MODEL_REGISTRY, TIER_DEFAULTS, FAILOVER_CHAINS

print(f"Total models: {len(MODEL_REGISTRY)}")
print(f"\nProviders: {set(v['provider'] for v in MODEL_REGISTRY.values())}")
print(f"\nTiers: {set(v['tier'] for v in MODEL_REGISTRY.values())}")

# Print cost comparison
print("\nCost comparison (per 1M input tokens):")
for model_id, info in sorted(MODEL_REGISTRY.items(), key=lambda x: x[1]['input_cost_per_million']):
    print(f"  {info['display_name']}: ${info['input_cost_per_million']:.4f}")

# Calculate cost of a sample request
model = "gpt-4o"
prompt_tokens = 500
completion_tokens = 300
info = MODEL_REGISTRY[model]
cost = (prompt_tokens / 1e6 * info['input_cost_per_million']) + \
       (completion_tokens / 1e6 * info['output_cost_per_million'])
print(f"\nCost of {prompt_tokens}p+{completion_tokens}c tokens on {model}: ${cost:.6f}")
