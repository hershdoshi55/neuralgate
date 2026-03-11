from proxy.model_registry import MODEL_REGISTRY, TIER_DEFAULTS, FAILOVER_CHAINS


def select_model(
    requested_model: str,
    complexity_result: dict,
    prompt_tokens: int,
    preferred_provider: str | None = None,
    max_cost_per_request: float | None = None,
) -> tuple[str, list[str]]:
    """
    Select the best model and return (primary_model, failover_chain).

    Args:
        requested_model: What the client asked for ("auto", "cheapest", specific name)
        complexity_result: Output of classify_complexity()
        prompt_tokens: Number of tokens in the prompt
        preferred_provider: Optional provider preference ("anthropic", "openai", etc.)
        max_cost_per_request: Optional cost cap in USD

    Returns:
        (selected_model_id, failover_chain)
    """
    tier = complexity_result["tier"]

    # Handle special model aliases
    if requested_model == "auto":
        target_tier = tier
    elif requested_model == "cheapest":
        target_tier = "cheap"
    elif requested_model in ("best", "most-capable"):
        target_tier = "frontier"
    elif requested_model == "balanced":
        target_tier = "mid"
    elif requested_model in MODEL_REGISTRY:
        # Specific model requested — use it directly
        return requested_model, FAILOVER_CHAINS.get(
            MODEL_REGISTRY[requested_model]["tier"], []
        )
    else:
        # Unknown model — default to auto routing
        target_tier = tier

    # Use the tier default as primary unless a constraint forces a different choice
    default_model = TIER_DEFAULTS.get(target_tier)
    failover_chain = FAILOVER_CHAINS.get(target_tier, [])

    # Check if the default fits and no constraints override it
    def _fits(model_id: str) -> bool:
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            return False
        if info["context_window"] <= prompt_tokens + 500:
            return False
        if preferred_provider and info["provider"] != preferred_provider:
            return False
        if max_cost_per_request:
            est_cost = (
                prompt_tokens / 1_000_000 * info["input_cost_per_million"] +
                500 / 1_000_000 * info["output_cost_per_million"]
            )
            if est_cost > max_cost_per_request:
                return False
        return True

    if default_model and _fits(default_model):
        selected = default_model
        failover = [m for m in failover_chain if m != selected]
        return selected, failover

    # Default doesn't fit constraints — pick from full tier candidate list
    candidates = [
        model_id for model_id, info in MODEL_REGISTRY.items()
        if info["tier"] == target_tier and _fits(model_id)
    ]

    # Escalate tier if nothing fits context window
    if not candidates:
        for escalate_tier in ["mid", "frontier"]:
            if escalate_tier == target_tier:
                continue
            candidates = [
                m for m in MODEL_REGISTRY
                if MODEL_REGISTRY[m]["tier"] == escalate_tier and _fits(m)
            ]
            if candidates:
                break

    if not candidates:
        candidates = sorted(
            MODEL_REGISTRY.keys(),
            key=lambda m: MODEL_REGISTRY[m]["context_window"],
            reverse=True
        )

    # Among constrained candidates, prefer cheapest
    candidates.sort(key=lambda m: MODEL_REGISTRY[m]["input_cost_per_million"])
    selected = candidates[0]
    failover = [m for m in failover_chain if m != selected]

    return selected, failover
