from proxy.model_registry import MODEL_REGISTRY, TIER_DEFAULTS


def calculate_cost(model_info: dict, prompt_tokens: int, completion_tokens: int) -> tuple[float, float]:
    """
    Calculate actual cost in USD for a request.

    Returns: (input_cost_usd, output_cost_usd)
    """
    input_cost = (prompt_tokens / 1_000_000) * model_info["input_cost_per_million"]
    output_cost = (completion_tokens / 1_000_000) * model_info["output_cost_per_million"]
    return input_cost, output_cost


def calculate_frontier_cost(tier: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate what this request WOULD have cost on the default model for its tier.
    Used to compute cost savings from intelligent routing.

    If a cheap-tier request was routed to claude-haiku but the frontier model for
    cheap tier is also claude-haiku, savings=0. But if a mid-tier request was routed
    to deepseek-chat instead of claude-sonnet (default mid), we calculate the delta.

    The "baseline" is always the default model for the complexity tier detected.
    """
    baseline_model_id = TIER_DEFAULTS.get(tier)
    if not baseline_model_id:
        return 0.0

    baseline_info = MODEL_REGISTRY.get(baseline_model_id, {})
    if not baseline_info:
        return 0.0

    input_cost = (prompt_tokens / 1_000_000) * baseline_info["input_cost_per_million"]
    output_cost = (completion_tokens / 1_000_000) * baseline_info["output_cost_per_million"]
    return input_cost + output_cost
