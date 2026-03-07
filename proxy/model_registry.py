# proxy/model_registry.py

MODEL_REGISTRY = {

    # ═══════════════════════════════════════════════════════
    # ANTHROPIC
    # Pricing: https://www.anthropic.com/pricing
    # ═══════════════════════════════════════════════════════

    "claude-opus-4-5": {
        "provider": "anthropic",
        "display_name": "Claude Opus 4.5",
        "tier": "frontier",
        "context_window": 200_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 15.00,
        "output_cost_per_million": 75.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Anthropic's most capable model. Best for complex reasoning, nuanced writing, advanced coding.",
        "latency_tier": "slow",
    },

    "claude-sonnet-4-5": {
        "provider": "anthropic",
        "display_name": "Claude Sonnet 4.5",
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

    "claude-haiku-4-5": {
        "provider": "anthropic",
        "display_name": "Claude Haiku 4.5",
        "tier": "cheap",
        "context_window": 200_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 0.80,
        "output_cost_per_million": 4.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Fastest and most affordable Claude. Great for simple Q&A, classification, extraction.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # OPENAI
    # Pricing: https://openai.com/api/pricing
    # ═══════════════════════════════════════════════════════

    "gpt-4o": {
        "provider": "openai",
        "display_name": "GPT-4o",
        "tier": "frontier",
        "context_window": 128_000,
        "max_output_tokens": 16_384,
        "input_cost_per_million": 2.50,
        "output_cost_per_million": 10.00,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "OpenAI's flagship model. Strong at reasoning, coding, and multimodal tasks.",
        "latency_tier": "medium",
    },

    "gpt-4o-mini": {
        "provider": "openai",
        "display_name": "GPT-4o Mini",
        "tier": "mid",
        "context_window": 128_000,
        "max_output_tokens": 16_384,
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Highly capable and very affordable. Handles most tasks well.",
        "latency_tier": "fast",
    },

    "o3-mini": {
        "provider": "openai",
        "display_name": "o3-mini",
        "tier": "frontier",
        "context_window": 200_000,
        "max_output_tokens": 100_000,
        "input_cost_per_million": 1.10,
        "output_cost_per_million": 4.40,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "OpenAI's reasoning model. Best for math, logic, and multi-step problem solving.",
        "latency_tier": "slow",
    },

    # ═══════════════════════════════════════════════════════
    # GOOGLE
    # Pricing: https://ai.google.dev/pricing
    # ═══════════════════════════════════════════════════════

    "gemini-1.5-pro": {
        "provider": "google",
        "display_name": "Gemini 1.5 Pro",
        "tier": "frontier",
        "context_window": 2_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 3.50,
        "output_cost_per_million": 10.50,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Google's most capable model. Industry-leading context window. Great for long documents.",
        "latency_tier": "medium",
    },

    "gemini-1.5-flash": {
        "provider": "google",
        "display_name": "Gemini 1.5 Flash",
        "tier": "mid",
        "context_window": 1_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.075,
        "output_cost_per_million": 0.30,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Extremely fast and very cheap. Good for high-volume workloads.",
        "latency_tier": "fast",
    },

    "gemini-1.5-flash-8b": {
        "provider": "google",
        "display_name": "Gemini 1.5 Flash 8B",
        "tier": "cheap",
        "context_window": 1_000_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.0375,
        "output_cost_per_million": 0.15,
        "supports_system_prompt": True,
        "supports_vision": True,
        "description": "Smallest Gemini model. Best for simple extraction, classification, summaries.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # XAI (GROK)
    # Pricing: https://x.ai/api
    # ═══════════════════════════════════════════════════════

    "grok-2": {
        "provider": "xai",
        "display_name": "Grok 2",
        "tier": "frontier",
        "context_window": 131_072,
        "max_output_tokens": 4096,
        "input_cost_per_million": 2.00,
        "output_cost_per_million": 10.00,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "xAI's flagship model. OpenAI-compatible API. Good for general tasks.",
        "latency_tier": "medium",
    },

    "grok-2-mini": {
        "provider": "xai",
        "display_name": "Grok 2 Mini",
        "tier": "mid",
        "context_window": 131_072,
        "max_output_tokens": 4096,
        "input_cost_per_million": 0.20,
        "output_cost_per_million": 0.50,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "Smaller, faster Grok model.",
        "latency_tier": "fast",
    },

    # ═══════════════════════════════════════════════════════
    # DEEPSEEK
    # Pricing: https://api-docs.deepseek.com/quick_start/pricing
    # ═══════════════════════════════════════════════════════

    "deepseek-chat": {
        "provider": "deepseek",
        "display_name": "DeepSeek-V3",
        "tier": "mid",
        "context_window": 64_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.27,
        "output_cost_per_million": 1.10,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "DeepSeek's flagship chat model. Exceptional value — frontier-class at mid-tier pricing.",
        "latency_tier": "medium",
    },

    "deepseek-reasoner": {
        "provider": "deepseek",
        "display_name": "DeepSeek-R1",
        "tier": "frontier",
        "context_window": 64_000,
        "max_output_tokens": 8192,
        "input_cost_per_million": 0.55,
        "output_cost_per_million": 2.19,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "DeepSeek's reasoning model (like o1). Strong at math and logic at a fraction of OpenAI o3 pricing.",
        "latency_tier": "slow",
    },

    # ═══════════════════════════════════════════════════════
    # MISTRAL
    # Pricing: https://mistral.ai/technology/#pricing
    # ═══════════════════════════════════════════════════════

    "mistral-large-latest": {
        "provider": "mistral",
        "display_name": "Mistral Large",
        "tier": "frontier",
        "context_window": 128_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 2.00,
        "output_cost_per_million": 6.00,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "Mistral's most capable model. Strong at code and multilingual tasks.",
        "latency_tier": "medium",
    },

    "mistral-small-latest": {
        "provider": "mistral",
        "display_name": "Mistral Small",
        "tier": "cheap",
        "context_window": 128_000,
        "max_output_tokens": 4096,
        "input_cost_per_million": 0.20,
        "output_cost_per_million": 0.60,
        "supports_system_prompt": True,
        "supports_vision": False,
        "description": "Very affordable. Good for classification, summarization, extraction.",
        "latency_tier": "fast",
    },
}

# Tier ordering for routing decisions
TIER_ORDER = ["cheap", "mid", "frontier"]

# Default model per tier — used when no preference specified
TIER_DEFAULTS = {
    "cheap": "claude-haiku-4-5",
    "mid": "claude-sonnet-4-5",
    "frontier": "claude-opus-4-5",
}

# Failover chains: if primary fails, try these in order
FAILOVER_CHAINS = {
    "frontier": ["claude-opus-4-5", "gpt-4o", "gemini-1.5-pro", "grok-2"],
    "mid": ["claude-sonnet-4-5", "gpt-4o-mini", "gemini-1.5-flash", "deepseek-chat"],
    "cheap": ["claude-haiku-4-5", "gpt-4o-mini", "gemini-1.5-flash-8b", "mistral-small-latest"],
}
