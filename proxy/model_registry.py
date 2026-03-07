# proxy/model_registry.py

MODEL_REGISTRY = {

    # ═══════════════════════════════════════════════════════
    # ANTHROPIC
    # Pricing: https://www.anthropic.com/pricing
    # ═══════════════════════════════════════════════════════

    "claude-opus-4-6": {
        "provider": "anthropic",
        "display_name": "Claude Opus 4.6",
        "tier": "frontier",
        "context_window": 200_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 5.00,
        "output_cost_per_million": 25.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Anthropic's most capable model. Best for complex reasoning, nuanced writing, advanced coding.",
        "latency_tier": "slow",
    },

    "claude-sonnet-4-6": {
        "provider": "anthropic",
        "display_name": "Claude Sonnet 4.6",
        "tier": "mid",
        "context_window": 200_000,
        "max_output_tokens": 8096,
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Excellent balance of capability and cost. Best for most production workloads.",
        "latency_tier": "medium",
    },

    "claude-haiku-4-5-20251001": {
        "provider": "anthropic",
        "display_name": "Claude Haiku 4.5",
        "tier": "cheap",
        "context_window": 200_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 1.00,
        "output_cost_per_million": 5.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Fastest and most affordable Claude. Great for simple Q&A, classification, extraction.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # OPENAI
    # Pricing: https://openai.com/api/pricing
    # ═══════════════════════════════════════════════════════

    "gpt-5.4": {
        "provider": "openai",
        "display_name": "GPT-5.4",
        "tier": "frontier",
        "context_window": 128_000,
        "max_output_tokens": 16_384,
        "input_cost_per_million": 2.50,
        "output_cost_per_million": 15.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "OpenAI's most capable model. Best for complex reasoning, coding, and professional work.",
        "latency_tier": "slow",
    },

    "gpt-5-mini": {
        "provider": "openai",
        "display_name": "GPT-5 Mini",
        "tier": "mid",
        "context_window": 128_000,
        "max_output_tokens": 16_384,
        "input_cost_per_million": 0.25,
        "output_cost_per_million": 2.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Fast and capable GPT-5 variant. Great balance of quality and cost.",
        "latency_tier": "fast",
    },

    "gpt-5-nano": {
        "provider": "openai",
        "display_name": "GPT-5 Nano",
        "tier": "cheap",
        "context_window": 128_000,
        "max_output_tokens": 16_384,
        "input_cost_per_million": 0.05,
        "output_cost_per_million": 0.40,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Smallest and cheapest GPT-5 model. Best for simple classification and extraction.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # GOOGLE
    # Pricing: https://ai.google.dev/pricing
    # All three models have a free tier — no payment required
    # ═══════════════════════════════════════════════════════

    "gemini-2.5-pro": {
        "provider": "google",
        "display_name": "Gemini 2.5 Pro",
        "tier": "frontier",
        "context_window": 1_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 10.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Google's most capable stable model. Excels at coding and complex reasoning. Free tier available.",
        "latency_tier": "medium",
    },

    "gemini-2.5-flash": {
        "provider": "google",
        "display_name": "Gemini 2.5 Flash",
        "tier": "mid",
        "context_window": 1_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.30,
        "output_cost_per_million": 2.50,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Fast hybrid reasoning model. Great balance of speed and intelligence. Free tier available.",
        "latency_tier": "fast",
    },

    "gemini-2.5-flash-lite": {
        "provider": "google",
        "display_name": "Gemini 2.5 Flash-Lite",
        "tier": "cheap",
        "context_window": 1_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.10,
        "output_cost_per_million": 0.40,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Smallest and most cost-efficient Gemini model. Built for high-volume tasks. Free tier available.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # DEEPSEEK
    # Pricing: https://api-docs.deepseek.com/quick_start/pricing
    # ═══════════════════════════════════════════════════════

    "deepseek-chat": {
        "provider": "deepseek",
        "display_name": "DeepSeek V3.2",
        "tier": "mid",
        "context_window": 128_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.28,
        "output_cost_per_million": 0.42,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "DeepSeek's flagship chat model. Exceptional value — frontier-class quality at mid-tier pricing.",
        "latency_tier": "medium",
    },

    "deepseek-reasoner": {
        "provider": "deepseek",
        "display_name": "DeepSeek R1 (Thinking)",
        "tier": "frontier",
        "context_window": 128_000,
        "max_output_tokens": 64_000,
        "input_cost_per_million": 0.28,
        "output_cost_per_million": 0.42,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "DeepSeek's reasoning model with thinking mode. Strong at math and logic at minimal cost.",
        "latency_tier": "slow",
    },
}

# Tier ordering for routing decisions
TIER_ORDER = ["cheap", "mid", "frontier"]

# Default model per tier — used when no preference specified
TIER_DEFAULTS = {
    "cheap": "claude-haiku-4-5-20251001",
    "mid": "claude-sonnet-4-6",
    "frontier": "claude-opus-4-6",
}

# Failover chains: if primary fails, try these in order
FAILOVER_CHAINS = {
    "frontier": ["claude-opus-4-6", "gpt-5.4", "gemini-2.5-pro", "deepseek-reasoner"],
    "mid": ["claude-sonnet-4-6", "gpt-5-mini", "gemini-2.5-flash", "deepseek-chat"],
    "cheap": ["claude-haiku-4-5-20251001", "gpt-5-nano", "gemini-2.5-flash-lite"],
}
