import re
import tiktoken

# Keywords that indicate HARD tasks (push score up)
COMPLEX_SIGNALS = {
    # Reasoning words
    "analyze": 0.28, "analyse": 0.28, "critique": 0.15, "evaluate": 0.15,
    "compare": 0.10, "contrast": 0.10, "synthesize": 0.15, "synthesiz": 0.15, "argue": 0.12,
    "reason": 0.10, "explain why": 0.12, "justify": 0.10, "assess": 0.10,
    "step by step": 0.15, "think through": 0.15, "pros and cons": 0.10,

    # Technical/coding words
    "implement": 0.12, "algorithm": 0.15, "optimize": 0.12, "debug": 0.10,
    "architecture": 0.12, "design pattern": 0.15, "complexity": 0.10,
    "refactor": 0.10, "review this code": 0.12,

    # Creative / nuanced writing
    "write a story": 0.12, "persuasive essay": 0.20, "creative": 0.08,
    "poem": 0.08, "nuanced": 0.12, "sophisticated": 0.10,

    # Research / depth
    "research": 0.10, "comprehensive": 0.12, "in-depth": 0.12,
    "detailed": 0.08, "thorough": 0.10,
}

# Keywords that indicate EASY tasks (push score down)
SIMPLE_SIGNALS = {
    "what is": -0.10, "define": -0.12, "list": -0.08, "give me": -0.05,
    "translate": -0.10, "summarize": -0.08, "summarise": -0.08,
    "convert": -0.10, "what does": -0.08, "who is": -0.10,
    "when was": -0.08, "how many": -0.05, "yes or no": -0.15,
    "true or false": -0.15, "fix this typo": -0.15, "correct this": -0.08,
}

enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def classify_complexity(messages: list[dict]) -> dict:
    """
    Analyze a list of messages and return a complexity score + reasoning.

    Returns:
        {
            "score": 0.72,          # 0.0 (trivial) to 1.0 (maximum complexity)
            "tier": "frontier",     # "cheap", "mid", or "frontier"
            "signals": [...],       # Which signals fired
            "total_tokens": 1240,   # Total tokens across all messages
            "reasoning": "..."      # Human-readable explanation
        }
    """
    score = 0.40  # Start at neutral mid-point, not 0
    signals_fired = []

    # Combine all message content for analysis
    full_text = " ".join(
        msg.get("content", "") for msg in messages
        if isinstance(msg.get("content"), str)
    ).lower()

    total_tokens = count_tokens(full_text)

    # ── Signal 1: Prompt length ────────────────────────────────────────────
    if total_tokens < 30:
        score -= 0.08
        signals_fired.append(f"very_short_prompt ({total_tokens} tokens, -0.08)")
    elif total_tokens < 80:
        score -= 0.08
        signals_fired.append(f"short_prompt ({total_tokens} tokens, -0.08)")
    elif total_tokens > 500:
        score += 0.10
        signals_fired.append(f"long_prompt ({total_tokens} tokens, +0.10)")
    elif total_tokens > 1500:
        score += 0.20
        signals_fired.append(f"very_long_prompt ({total_tokens} tokens, +0.20)")

    # ── Signal 2: Code presence ────────────────────────────────────────────
    if "```" in full_text or "def " in full_text or "function " in full_text:
        score += 0.15
        signals_fired.append("code_detected (+0.15)")

    # ── Signal 3: Multi-turn conversation ─────────────────────────────────
    num_turns = len([m for m in messages if m.get("role") == "user"])
    if num_turns >= 5:
        score += 0.10
        signals_fired.append(f"long_conversation ({num_turns} turns, +0.10)")
    elif num_turns >= 10:
        score += 0.20
        signals_fired.append(f"very_long_conversation ({num_turns} turns, +0.20)")

    # ── Signal 4: Complex keyword matching ────────────────────────────────
    for keyword, weight in COMPLEX_SIGNALS.items():
        if keyword in full_text:
            score += weight
            signals_fired.append(f"keyword:'{keyword}' (+{weight})")

    # ── Signal 5: Simple keyword matching ─────────────────────────────────
    for keyword, weight in SIMPLE_SIGNALS.items():
        if keyword in full_text:
            score += weight  # weight is negative
            signals_fired.append(f"keyword:'{keyword}' ({weight})")

    # ── Signal 6: Question mark only (simple question pattern) ────────────
    if full_text.strip().endswith("?") and total_tokens < 50:
        score -= 0.10
        signals_fired.append("simple_question_pattern (-0.10)")

    # Clamp score to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    # Map score to tier
    if score < 0.35:
        tier = "cheap"
    elif score < 0.60:
        tier = "mid"
    else:
        tier = "frontier"

    reasoning = (
        f"Score {score:.2f}: {len(signals_fired)} signals fired. "
        f"Total prompt tokens: {total_tokens}. "
        f"Routed to {tier} tier."
    )

    return {
        "score": round(score, 3),
        "tier": tier,
        "signals": signals_fired,
        "total_tokens": total_tokens,
        "reasoning": reasoning,
    }
