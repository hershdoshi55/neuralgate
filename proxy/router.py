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

    # Filter candidates by tier
    candidates = [
        model_id for model_id, info in MODEL_REGISTRY.items()
        if info["tier"] == target_tier
    ]

    # Filter by context window — prompt must fit
    candidates = [
        m for m in candidates
        if MODEL_REGISTRY[m]["context_window"] > prompt_tokens + 500
        # +500 buffer for output tokens
    ]

    # If no candidates fit context window, escalate to next tier
    if not candidates:
        next_tier_idx = ["cheap", "mid", "frontier"].index(target_tier) + 1
        if next_tier_idx < 3:
            next_tier = ["cheap", "mid", "frontier"][next_tier_idx]
            candidates = [
                m for m in MODEL_REGISTRY
                if MODEL_REGISTRY[m]["tier"] == next_tier
                and MODEL_REGISTRY[m]["context_window"] > prompt_tokens + 500
            ]

    if not candidates:
        # Nothing fits — return largest context model
        candidates = sorted(
            MODEL_REGISTRY.keys(),
            key=lambda m: MODEL_REGISTRY[m]["context_window"],
            reverse=True
        )

    # Apply preferred provider filter if specified
    if preferred_provider:
        provider_candidates = [
            m for m in candidates
            if MODEL_REGISTRY[m]["provider"] == preferred_provider
        ]
        if provider_candidates:
            candidates = provider_candidates

    # Apply cost cap if specified
    if max_cost_per_request:
        cost_filtered = []
        for m in candidates:
            info = MODEL_REGISTRY[m]
            # Estimate cost for a typical response (500 output tokens)
            est_cost = (
                prompt_tokens / 1_000_000 * info["input_cost_per_million"] +
                500 / 1_000_000 * info["output_cost_per_million"]
            )
            if est_cost <= max_cost_per_request:
                cost_filtered.append(m)
        if cost_filtered:
            candidates = cost_filtered

    # Sort candidates: prefer cheapest within the tier
    candidates.sort(
        key=lambda m: MODEL_REGISTRY[m]["input_cost_per_million"]
    )

    selected = candidates[0]
    failover = [m for m in FAILOVER_CHAINS.get(target_tier, []) if m != selected]

    return selected, failover
