# NeuralGate — Intelligent LLM Cost-Optimization Proxy
## Complete Implementation Guide — PRD v1.0

> **Who this document is for:** Someone who knows basic Python and has built a simple API before, but has never built an LLM infrastructure layer. Every concept is explained from scratch. Every file is described. Every step tells you exactly what to create and exactly what to search if you get stuck.

**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 · Redis 7 · Docker Compose · React  
**Estimated build time:** 7 days full-time (aggressive but doable)  
**Lines of code (approximate):** ~2,500  
**OpenAI-compatible:** Yes — drop-in replacement for any app using the OpenAI SDK

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Why This Project Exists — Portfolio Framing](#2-why-this-project-exists)
3. [Every Concept Explained From Scratch](#3-every-concept-explained-from-scratch)
4. [The Model Registry — Every Supported Model](#4-the-model-registry)
5. [The Routing Engine — How Decisions Are Made](#5-the-routing-engine)
6. [System Architecture](#6-system-architecture)
7. [Database Schema — Every Table and Column](#7-database-schema)
8. [API Specification — Every Endpoint](#8-api-specification)
9. [Component Implementation Details](#9-component-implementation-details)
10. [Caching Layer](#10-caching-layer)
11. [Observability — Metrics and Dashboard](#11-observability)
12. [Complete File Architecture](#12-complete-file-architecture)
13. [Docker Compose — Full Configuration](#13-docker-compose)
14. [Day-by-Day Implementation Guide](#14-day-by-day-implementation-guide)
15. [Load Testing and Benchmarking](#15-load-testing-and-benchmarking)
16. [Design Tradeoffs](#16-design-tradeoffs)
17. [Interview Preparation](#17-interview-preparation)
18. [Resume Bullets](#18-resume-bullets)

---

## 1. What This Project Is

### The one-sentence version

A reverse proxy that sits between your application and every major LLM provider — OpenAI, Anthropic, Google, xAI, DeepSeek — automatically routing each request to the cheapest model capable of handling it, while tracking cost, latency, and quality across every call.

### The longer version

Every company building LLM-powered products faces the same problem: LLMs are expensive, but you need quality. Claude Opus is brilliant but costs 75x more than Claude Haiku per token. GPT-4o is capable but GPT-4o-mini handles 90% of tasks at 1/20th the price. DeepSeek-V3 is shockingly capable and costs almost nothing compared to frontier models.

The insight: **not all requests need your best model.** A user asking "summarize this sentence" doesn't need Claude Opus. A user asking for a nuanced legal analysis might. If you can classify request complexity before sending it to a model, you can route cheap requests to cheap models and expensive requests to expensive models — and save 60-80% on inference costs without any perceptible quality degradation.

This project is the infrastructure that does exactly that:

1. Client sends a chat completion request to your proxy (same format as OpenAI's API)
2. Proxy classifies the prompt complexity using a fast heuristic scoring system
3. Proxy selects the optimal model from the registry based on complexity + cost constraints
4. Proxy forwards the request to the appropriate provider (OpenAI, Anthropic, Google, etc.)
5. Proxy normalizes the response back to OpenAI format (so the client never knows which model ran)
6. Proxy logs every request: tokens used, cost, latency, model selected, complexity score
7. Dashboard shows cost breakdown, routing decisions, and savings vs always using the expensive model

### What you are building and NOT building

**You ARE building:**
- An OpenAI-compatible proxy API (`POST /v1/chat/completions`)
- A prompt complexity classifier (heuristic-based, no ML training required)
- A model registry with pricing for 15+ models across 6 providers
- A routing engine that selects optimal model based on complexity + cost budget
- Semantic caching: identical/similar prompts return cached responses without hitting any LLM
- Per-request logging: model used, tokens, cost, latency, complexity score
- Cost analytics API and React dashboard
- Provider failover: if OpenAI is down, route to Anthropic automatically

**You are NOT building:**
- Fine-tuning any models
- Training a classifier (the classifier is heuristic/rule-based)
- A chat UI (you're building the infrastructure layer)
- User authentication (out of scope for v1)
- Streaming responses (mentioned in Design Tradeoffs)

### What "OpenAI-compatible" means and why it matters

OpenAI established the de facto standard API format for chat completion:

```python
# Client code (this never changes regardless of which model actually runs)
from openai import OpenAI

client = OpenAI(
    api_key="your-proxy-key",
    base_url="http://localhost:8000/v1"  # Points to YOUR proxy, not OpenAI
)

response = client.chat.completions.create(
    model="auto",  # Special model name — proxy decides actual model
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
```

Your proxy receives this request, routes it to whatever model is optimal, and returns a response in exactly the same format as OpenAI would. The client code never changes. This is how companies like LiteLLM, OpenRouter, and Portkey work. You're building a simplified but production-pattern version of this.

### Real-world equivalents

| Real product | What it is |
|---|---|
| LiteLLM | Open-source LLM proxy — you're building a simpler version |
| OpenRouter | Multi-model routing service — same concept |
| Portkey | LLM gateway with analytics — what you're building |
| AWS Bedrock | Managed multi-model API — enterprise version |
| Martian | AI router startup (YC-backed) — exactly this |

When an interviewer hears "LLM proxy with intelligent routing," they immediately understand it. This is a real category of infrastructure product with funded startups behind it.

---

## 2. Why This Project Exists

### Portfolio framing

LLM infrastructure is one of the highest-demand engineering areas right now. Every company building on top of LLMs needs to solve:
- Cost control (inference is expensive at scale)
- Provider redundancy (single-provider dependency is a risk)
- Observability (what are we actually spending money on?)
- Latency optimization (match model capability to task requirements)

When you build this from scratch, you can speak fluently about:
- How different LLM APIs differ under the hood (Anthropic vs OpenAI vs Google have different request/response formats)
- Token counting and cost modeling for production inference workloads
- Semantic caching — why it's different from exact-match caching and how it works
- Prompt classification heuristics — what signals indicate a hard vs easy prompt
- Provider failover patterns
- The build vs buy decision for LLM infrastructure (when to use LiteLLM vs build your own)

### Who will be impressed

**AI startups:** This is literally their infrastructure problem. If you've built a routing layer you understand their stack.

**Any company with LLM costs:** Every team that has hit a surprise OpenAI bill at the end of the month wishes they had routing. You've built the solution.

**FAANG ML platform teams:** Cost optimization at scale is a core concern. Token budgeting, model selection, caching — these are real platform engineering problems.

---

## 3. Every Concept Explained From Scratch

Read this entire section before writing any code.

---

### 3.1 What a Reverse Proxy Is

A **proxy** sits between a client and a server and forwards requests on the client's behalf.

A **reverse proxy** sits in front of one or more servers and handles requests on the server's behalf.

```
Without proxy:
  Your App ──────────────────────────────→ OpenAI API

With NeuralGate:
  Your App ──→ NeuralGate ──→ OpenAI API
                           ──→ Anthropic API
                           ──→ Google API
                           ──→ DeepSeek API
```

Your app thinks it's talking to OpenAI. It sends exactly the same requests. NeuralGate intercepts them, makes decisions, and forwards to whatever backend is best.

**What to search:** "reverse proxy explained", "nginx reverse proxy tutorial"

---

### 3.2 LLM API Basics — Tokens, Prompts, Completions

**Tokens:** LLMs don't process words — they process tokens. A token is roughly 0.75 words in English. "Hello world" is 2 tokens. "Supercalifragilistic" is 5 tokens. Token count determines both cost and whether a request fits in the model's context window.

**Prompt tokens:** The tokens in the input (your messages).

**Completion tokens:** The tokens in the output (the model's response).

**Cost:** Every provider charges separately for input tokens and output tokens. Output tokens cost more because generating them is computationally expensive (sequential autoregressive decoding).

Example: GPT-4o charges $2.50 per million input tokens and $10.00 per million output tokens.
A request with a 500-token prompt and 300-token response costs:
`(500 / 1,000,000 × $2.50) + (300 / 1,000,000 × $10.00) = $0.00125 + $0.00300 = $0.00425`

**Context window:** The maximum number of tokens (input + output combined) a model can handle. GPT-4o supports 128,000 tokens. Some requests need large context windows (analyzing a long document). If the prompt is 90,000 tokens, you can't send it to a model with a 32,000 token window.

**What to search:** "LLM tokens explained", "tiktoken count tokens python", "OpenAI pricing calculator"

---

### 3.3 Why Different Models Exist

The LLM landscape has converged on a tiered model strategy:

**Frontier / flagship models:** Maximum capability. Used for complex reasoning, nuanced writing, hard coding problems. Expensive.
- Claude Opus 4.5, GPT-4o, Gemini 1.5 Pro

**Mid-tier models:** 80-90% of flagship capability at 20-40% of the cost. Good for most tasks.
- Claude Sonnet 4.5, GPT-4o-mini, Gemini 1.5 Flash

**Fast / cheap models:** Simple tasks, high volume, latency-sensitive. Minimal cost.
- Claude Haiku 3.5, GPT-4o-mini, Gemini Flash 8B, DeepSeek-V3

**The routing hypothesis:** If you can accurately classify which tier a request needs, you save enormous amounts of money. A company spending $10,000/month on GPT-4o for all requests might spend $2,000-3,000/month with intelligent routing — same quality on hard tasks, cheaper models on easy ones.

---

### 3.4 Prompt Complexity Classification

The core intelligence of the router. How do you know if a request is "hard" or "easy" before sending it to a model?

**You use heuristics — signals that correlate with complexity:**

**Signal 1: Prompt length**
Longer prompts usually indicate more complex tasks. A 10-word prompt is usually a simple question. A 500-word prompt with detailed instructions usually needs a capable model.

**Signal 2: Keywords indicating complexity**
Words like "analyze," "critique," "compare," "synthesize," "reason," "evaluate," "explain step by step" correlate with hard tasks.
Words like "summarize," "list," "what is," "define," "translate" correlate with easy tasks.

**Signal 3: Code presence**
If the prompt contains code blocks or mentions specific programming concepts, it likely needs a capable coding model.

**Signal 4: Message count (conversation length)**
A long back-and-forth conversation requires more context retention and usually benefits from a more capable model.

**Signal 5: Explicit complexity hints**
Some applications can pass metadata: `"X-Complexity-Hint: high"` in headers, or a `complexity` field in the request body.

**The output:** A complexity score from 0.0 to 1.0. Score maps to a tier:
- 0.0 - 0.35: Simple → route to cheap tier
- 0.35 - 0.65: Medium → route to mid tier  
- 0.65 - 1.0: Complex → route to frontier tier

**What to search:** "heuristic text classification python", "prompt engineering complexity scoring"

---

### 3.5 Semantic Caching

**Exact-match caching:** Store the exact prompt as a key. If the same exact prompt comes in again, return the cached response. Problem: "What is 2+2?" and "What is 2 + 2?" are different strings but semantically identical. Exact-match misses this.

**Semantic caching:** Embed the prompt into a vector. When a new prompt comes in, embed it and check if any cached prompt's vector is within a similarity threshold. If "What is the capital of France?" and "Which city is the capital of France?" are both in cache, the second one hits the cache because they're semantically equivalent.

**The pipeline:**
```
New prompt arrives
  → Embed the prompt (fast, cheap — text-embedding model)
  → Search Redis for similar cached prompts
  → If similarity > 0.95: return cached response (no LLM call!)
  → If no cache hit: call LLM, store (embedding, response) in cache
```

**Why this saves money:** In production, many requests are near-identical. Customer support bots get "how do I reset my password" 1000 times a day. Without semantic cache, that's 1000 LLM calls. With semantic cache, it's 1 LLM call and 999 cache hits.

**What to search:** "semantic caching LLM redis", "vector similarity cache python"

---

### 3.6 Provider Failover

If OpenAI's API is down or rate-limiting you, your application fails. Single-provider dependency is a reliability risk. The router solves this: if the primary provider for a model tier returns an error (5xx, rate limit 429), automatically retry on an equivalent model from a different provider.

```
Request → route to gpt-4o → 429 Too Many Requests
  → failover: route to claude-sonnet-4-5 → success
  → log: {primary_model: "gpt-4o", actual_model: "claude-sonnet-4-5", failover: true}
```

**What to search:** "circuit breaker pattern python", "retry with fallback API calls"

---

### 3.7 OpenAI API Format — The Standard You're Implementing

Every provider has a slightly different API format. Your proxy's job is to translate between the universal "OpenAI format" your clients use and whatever format the actual provider expects.

**OpenAI format (what clients send you):**
```json
{
  "model": "auto",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "max_tokens": 100,
  "temperature": 0.7
}
```

**Anthropic format (what you send to Anthropic):**
```json
{
  "model": "claude-haiku-4-5",
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "max_tokens": 100
}
```

Key differences: Anthropic separates the system prompt from messages. Anthropic doesn't use `temperature` by default. You need adapters that translate between formats.

**Google Gemini format:**
```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "What is the capital of France?"}]}
  ],
  "generationConfig": {"maxOutputTokens": 100}
}
```

Completely different structure. Your adapter layer handles all of this transparently.

**What to search:** "OpenAI chat completions API reference", "Anthropic messages API reference", "Google Gemini API Python"

---

### 3.8 Token Counting

You need to count tokens before sending a request to:
1. Verify the prompt fits within the model's context window
2. Estimate cost before the request
3. Log actual cost after the response (providers return token counts in the response)

**For OpenAI models:** Use `tiktoken` library. `cl100k_base` encoding for GPT-4 family.

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
tokens = enc.encode("Hello, world!")
print(len(tokens))  # 4
```

**For Anthropic models:** Anthropic provides a token counting endpoint, or use their Python SDK's built-in counting.

**For a proxy:** Use tiktoken as an approximation for all models — it's close enough for routing decisions. Actual token counts come from the provider's API response.

**What to search:** "tiktoken count tokens python tutorial"

---

### 3.9 Cost Tracking

Every request has a calculable cost:

```python
cost = (input_tokens / 1_000_000 * input_price_per_million) + \
       (output_tokens / 1_000_000 * output_price_per_million)
```

You store this per request in PostgreSQL. Then you can query:
- Total spend by day/week/month
- Spend by model
- Average cost per request
- Savings vs always using frontier model
- Cost breakdown by complexity tier

The "savings" metric is particularly powerful for a portfolio project: you can show a concrete dollar amount saved by routing intelligently vs sending everything to GPT-4o.

---

### 3.10 Proxy API Key Authentication

Right now any process that can reach port 8000 can use your proxy and spend your money. You need a gate. The simplest production-viable approach: require every request to include a static bearer token in the `Authorization` header. The proxy checks it in a FastAPI middleware before any request is processed.

```
Client request headers:
  Authorization: Bearer ng-your-secret-key-here
  Content-Type: application/json
```

If the key is missing or wrong, return `401 Unauthorized` immediately — no routing, no LLM calls, no cost. The key lives in `.env` as `PROXY_API_KEY` and is never committed to the repo.

This is not a full user auth system (no database of users, no JWT, no sign-up flow). It's a single shared secret that controls access to the proxy — the same pattern used by OpenAI's own API key system at the most basic level. For a portfolio project running locally or in a demo, this is exactly the right level of security.

**What to search:** "FastAPI middleware authentication bearer token", "HTTP 401 unauthorized FastAPI"

---

### 3.11 Per-Client Rate Limiting

Even with an API key, a runaway script or misconfigured application could hammer your proxy and send thousands of requests to LLM providers in minutes, running up a massive bill. Rate limiting caps how many requests a given client can make in a time window.

**The mechanism — Redis sliding window counter:**

For each client ID (from the `X-Client-ID` header, or falling back to the API key), you maintain a counter in Redis that expires after the window duration. Every request increments the counter. If the counter exceeds the limit, return `429 Too Many Requests`.

```
Request arrives from client "my-app"
  → Redis: INCR rate:my-app → returns 47
  → 47 < 60 (limit per minute) → allow
  → Redis: EXPIRE rate:my-app 60 (reset after 1 minute)

Request arrives from client "my-app" (61st request this minute)
  → Redis: INCR rate:my-app → returns 61
  → 61 > 60 → return 429, Retry-After: 30s
```

**Why Redis and not Postgres?** Rate limit checks happen on every single request before any processing. They need to be sub-millisecond. Redis is an in-memory store — a counter increment takes ~0.2ms. A Postgres query would take 2-5ms and add overhead to every request.

**Configurable limits:** Different clients might have different limits. A production app gets 1000 requests/minute; a dev key gets 60/minute. Store limits per client in Redis or a config file.

**What to search:** "Redis rate limiting sliding window Python", "FastAPI rate limit middleware Redis"

---

### 3.12 Request Replay

The analytics dashboard shows every request — model used, cost, latency, complexity score. But sometimes you want to re-run a specific request: maybe it failed due to a provider outage, or you want to see if the routing decision would be different today after you tuned the classifier weights.

Request replay means: take a logged request from the database, reconstruct the original messages, and re-send it through the proxy as a fresh request. The new response is logged as a new request row, with a `replayed_from` field pointing to the original request ID.

**What's stored:** The `messages_hash` is in every request row, but the raw messages are not (privacy). To enable replay, you need to store the actual messages content — either in the requests table (simplest) or in a separate `request_payloads` table (better for privacy, lets you delete payloads without losing the cost/routing log).

**The dashboard UI:** A "Replay" button on each row in the LiveRequestFeed table. Click it, it calls `POST /requests/{request_id}/replay`, the proxy re-runs the request, the response appears in a modal showing: original model vs new model, original cost vs new cost, original latency vs new latency.

**What to search:** "FastAPI background tasks", "PostgreSQL JSONB store and retrieve Python"

---

## 4. The Model Registry

This is the heart of the routing system — the complete list of supported models with their capabilities and pricing.

### 4.1 Pricing Table (Current as of early 2026)

> **Important:** LLM pricing changes frequently. Always verify at each provider's pricing page before showing these numbers. These are approximate and for routing decision purposes — the actual cost is always computed from the provider's response token counts.

```python
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
        "latency_tier": "slow",  # relative
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
        "context_window": 2_000_000,  # 2M context — largest available
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
    # Note: DeepSeek is extraordinarily cheap. Verify pricing is current.
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
```

### 4.2 Provider API Keys Required

To use all providers you need API keys from:
- **Anthropic:** console.anthropic.com
- **OpenAI:** platform.openai.com
- **Google:** aistudio.google.com (free tier available)
- **xAI:** x.ai/api
- **DeepSeek:** platform.deepseek.com (very cheap, good for testing)
- **Mistral:** console.mistral.ai

For the portfolio project you don't need all of them. Start with **Anthropic + OpenAI** (you likely already have these). Add others as you go. The routing engine works with whatever providers you have keys for.

---

## 5. The Routing Engine

### 5.1 The Decision Flow

```
Request arrives: POST /v1/chat/completions
  │
  ├─ model = "auto"?
  │    ├─ YES → run complexity classifier → select tier → pick model
  │    └─ NO → model = "cheapest" / "fastest" / "most-capable"?
  │         ├─ map alias to tier → pick model
  │         └─ specific model named (e.g., "gpt-4o") → use that model directly
  │
  ├─ Check context window: does prompt fit?
  │    └─ If not: escalate to model with larger context window
  │
  ├─ Check semantic cache: similar prompt cached?
  │    └─ If yes: return cached response, log cache_hit=true, cost=$0
  │
  ├─ Check provider availability: is provider up?
  │    └─ If down: failover to next in chain
  │
  └─ Send to selected model → return response → log everything
```

### 5.2 The Complexity Classifier

```python
# proxy/classifier.py

import re
import tiktoken

# Keywords that indicate HARD tasks (push score up)
COMPLEX_SIGNALS = {
    # Reasoning words
    "analyze": 0.15, "analyse": 0.15, "critique": 0.15, "evaluate": 0.15,
    "compare": 0.10, "contrast": 0.10, "synthesize": 0.15, "argue": 0.12,
    "reason": 0.10, "explain why": 0.12, "justify": 0.10, "assess": 0.10,
    "step by step": 0.15, "think through": 0.15, "pros and cons": 0.10,

    # Technical/coding words
    "implement": 0.12, "algorithm": 0.15, "optimize": 0.12, "debug": 0.10,
    "architecture": 0.12, "design pattern": 0.15, "complexity": 0.10,
    "refactor": 0.10, "review this code": 0.12,

    # Creative / nuanced writing
    "write a story": 0.12, "persuasive essay": 0.15, "creative": 0.08,
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
    # Short prompts tend to be simple questions
    # Very long prompts are usually complex tasks
    if total_tokens < 30:
        score -= 0.15
        signals_fired.append(f"very_short_prompt ({total_tokens} tokens, -0.15)")
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
    # More messages = more context needed = harder task
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
    # "What is the capital of France?" → simple
    # Has very few tokens AND ends with a question → probably easy
    if full_text.strip().endswith("?") and total_tokens < 50:
        score -= 0.10
        signals_fired.append("simple_question_pattern (-0.10)")

    # Clamp score to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    # Map score to tier
    if score < 0.35:
        tier = "cheap"
    elif score < 0.65:
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
```

### 5.3 Model Selection Logic

```python
# proxy/router.py (selection logic)

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
```

---

## 6. System Architecture

### 6.1 Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATION                               │
│  (uses OpenAI SDK, base_url points to NeuralGate)                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ POST /v1/chat/completions
                           │ (OpenAI format)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     NEURALGATE API  (FastAPI)                       │
│                                                                     │
│  1. Parse request                                                   │
│  2. Count tokens (tiktoken)                                         │
│  3. Check semantic cache (Redis + embeddings)                       │
│  4. Classify complexity → select model → build failover chain       │
│  5. Adapt request format (OpenAI → provider format)                 │
│  6. Call provider API with failover                                 │
│  7. Adapt response (provider format → OpenAI format)                │
│  8. Store in semantic cache                                         │
│  9. Log request record to PostgreSQL                                │
│  10. Return OpenAI-format response                                  │
└────────┬─────────────────────────────────────────────────────────────┘
         │                          │ async log write
         │ provider calls           ▼
         │              ┌──────────────────────┐
         │              │     POSTGRESQL        │
         │              │   (request logs,      │
         │              │    cost tracking,     │
         │              │    analytics)         │
         │              └──────────────────────┘
         │
         │              ┌──────────────────────┐
         │              │       REDIS           │
         │              │  (semantic cache:     │
         │              │   prompt vectors +    │
         │              │   cached responses)   │
         │              └──────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────────────┐
│                    PROVIDER APIS                                   │
│                                                                    │
│  Anthropic          OpenAI          Google          DeepSeek      │
│  (claude-*)         (gpt-*)         (gemini-*)      (deepseek-*)  │
│                                                                    │
│  xAI (grok-*)       Mistral (mistral-*)                           │
└───────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   ANALYTICS + DASHBOARD                             │
│                                                                     │
│  GET /analytics/summary      → cost by day, model, tier            │
│  GET /analytics/routing      → routing decision breakdown           │
│  GET /analytics/savings      → vs always-frontier comparison        │
│  GET /analytics/cache        → cache hit rate, tokens saved         │
│  React Dashboard             → charts, live request feed           │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Request Flow — Detailed

```
T=0ms   POST /v1/chat/completions arrives
T=1ms   Parse body, validate with Pydantic
T=2ms   Count prompt tokens with tiktoken (~0.5ms)
T=3ms   Hash prompt for exact cache check (Redis GET ~0.3ms)
        → Exact cache miss → continue
T=4ms   Embed prompt for semantic cache check (OpenAI text-embedding-3-small, ~100ms)
        ← OR use cached embedding if we've seen this prompt before
T=6ms   Redis vector similarity search (~1ms)
        → Similarity > 0.95? Return cached response immediately (T=7ms total!)
        → Cache miss → continue
T=7ms   classify_complexity() → score=0.72, tier="frontier" (~0.2ms, pure Python)
T=8ms   select_model() → "claude-opus-4-5", failover=["gpt-4o", "gemini-1.5-pro"]
T=9ms   Build provider request (OpenAI → Anthropic format adapter)
T=10ms  Call Anthropic API...
        ...
T=850ms Anthropic responds
T=851ms Adapt response (Anthropic → OpenAI format)
T=852ms Store (prompt_embedding, response) in Redis semantic cache (async)
T=853ms INSERT request log into PostgreSQL (async, doesn't block response)
T=854ms Return OpenAI-format response to client

Total: ~854ms (dominated by LLM call latency)
Cache hit path: ~7ms (!!!!)
```

### 6.3 Semantic Cache Flow

```
New prompt: "What's the tallest mountain in the world?"

Step 1: Embed → [0.021, -0.043, 0.118, ...] (1536 floats)

Step 2: Redis search — find vectors within cosine distance 0.05
        Finds: "What is the highest mountain on Earth?" → similarity=0.97
        Threshold: 0.95
        → Cache HIT → return "Mount Everest at 8,849 meters" without calling LLM

New prompt: "Analyze the macroeconomic implications of Federal Reserve interest rate policy"

Step 2: Redis search — no vectors within threshold
        → Cache MISS → call LLM
        → Store embedding + response in Redis with TTL=24 hours
```

---

---

## 7. Database Schema

### 7.1 Migration Strategy

```
migrations/
  001_requests.sql       ← main request log table
  002_cache.sql          ← semantic cache metadata
  003_analytics.sql      ← materialized view for fast analytics
  004_security.sql       ← rate limit config + request payloads for replay
```

### 7.2 requests Table

```sql
-- migrations/001_requests.sql

CREATE TABLE requests (
    -- ── Identity ─────────────────────────────────────────────────────────
    request_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Unique ID for every request through the proxy

    -- ── Routing Decision ─────────────────────────────────────────────────
    requested_model     TEXT NOT NULL DEFAULT 'auto',
    -- What the client asked for: "auto", "cheapest", "gpt-4o", etc.

    selected_model      TEXT NOT NULL,
    -- What was actually used: "claude-haiku-4-5", "gpt-4o-mini", etc.

    selected_provider   TEXT NOT NULL,
    -- "anthropic", "openai", "google", "xai", "deepseek", "mistral"

    failover_occurred   BOOLEAN NOT NULL DEFAULT FALSE,
    -- True if primary model failed and we used a fallback

    original_model      TEXT,
    -- If failover_occurred: what was the primary model that failed

    -- ── Complexity Classification ─────────────────────────────────────────
    complexity_score    DECIMAL(4,3),
    -- 0.000 to 1.000

    complexity_tier     TEXT,
    -- "cheap", "mid", or "frontier"

    complexity_signals  JSONB,
    -- Array of signals that fired: ["keyword:analyze (+0.15)", ...]

    -- ── Token Counts ─────────────────────────────────────────────────────
    prompt_tokens       INT NOT NULL DEFAULT 0,
    completion_tokens   INT NOT NULL DEFAULT 0,
    total_tokens        INT GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,
    -- GENERATED column: auto-computed, no need to insert manually

    -- ── Cost ─────────────────────────────────────────────────────────────
    input_cost_usd      DECIMAL(12,8) NOT NULL DEFAULT 0,
    output_cost_usd     DECIMAL(12,8) NOT NULL DEFAULT 0,
    total_cost_usd      DECIMAL(12,8) GENERATED ALWAYS AS (input_cost_usd + output_cost_usd) STORED,

    frontier_cost_usd   DECIMAL(12,8),
    -- What this request WOULD have cost if routed to the tier's frontier model
    -- Used to calculate savings

    cost_savings_usd    DECIMAL(12,8) GENERATED ALWAYS AS
                        (COALESCE(frontier_cost_usd, 0) - (input_cost_usd + output_cost_usd)) STORED,
    -- Positive = money saved by routing away from frontier

    -- ── Cache ─────────────────────────────────────────────────────────────
    cache_hit           BOOLEAN NOT NULL DEFAULT FALSE,
    cache_similarity    DECIMAL(5,4),
    -- Similarity score if this was a semantic cache hit (0.0000 to 1.0000)

    -- ── Latency ──────────────────────────────────────────────────────────
    total_latency_ms    INT,
    -- Wall clock time from request received to response returned

    provider_latency_ms INT,
    -- Time spent waiting for the provider API (excludes classification, caching overhead)

    -- ── Request Content ──────────────────────────────────────────────────
    messages_hash       TEXT,
    -- SHA-256 of the messages array — used for exact cache lookup
    -- We don't store raw messages to avoid privacy issues

    message_count       INT NOT NULL DEFAULT 1,
    -- Number of messages in the conversation

    -- ── Response Metadata ────────────────────────────────────────────────
    finish_reason       TEXT,
    -- "stop", "length", "content_filter" — from provider response

    -- ── Client Context ────────────────────────────────────────────────────
    client_id           TEXT,
    -- Optional: identify which application/team is sending requests
    -- Passed as X-Client-ID header

    -- ── Timestamps ───────────────────────────────────────────────────────
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX idx_requests_created ON requests (created_at DESC);
-- Most common query: "requests in the last 24 hours"

CREATE INDEX idx_requests_model ON requests (selected_model, created_at DESC);
-- "cost breakdown by model"

CREATE INDEX idx_requests_provider ON requests (selected_provider, created_at DESC);
-- "cost breakdown by provider"

CREATE INDEX idx_requests_tier ON requests (complexity_tier, created_at DESC);
-- "routing distribution by tier"

CREATE INDEX idx_requests_cache ON requests (cache_hit, created_at DESC);
-- "cache hit rate over time"

CREATE INDEX idx_requests_client ON requests (client_id, created_at DESC)
    WHERE client_id IS NOT NULL;
-- "cost by client/team"

CREATE INDEX idx_requests_cost ON requests (total_cost_usd DESC);
-- "most expensive requests"
```

### 7.3 semantic_cache Table

```sql
-- migrations/002_cache.sql

-- Note: we use pgvector for semantic cache vector storage
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE semantic_cache (
    cache_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    messages_hash       TEXT UNIQUE NOT NULL,
    -- SHA-256 of exact messages — for exact-match fast path

    prompt_text         TEXT NOT NULL,
    -- The full prompt text (concatenated messages)
    -- Stored for debugging and similarity search result inspection

    prompt_embedding    vector(1536),
    -- OpenAI text-embedding-3-small output
    -- Used for semantic similarity search

    response_text       TEXT NOT NULL,
    -- The complete response content

    response_metadata   JSONB NOT NULL DEFAULT '{}',
    -- {model: "claude-haiku-4-5", finish_reason: "stop", prompt_tokens: 45, completion_tokens: 12}
    -- Stored so cache hits return realistic metadata

    hit_count           INT NOT NULL DEFAULT 0,
    -- How many times this cache entry has been used

    total_tokens_saved  INT NOT NULL DEFAULT 0,
    -- Sum of tokens not sent to LLMs due to this cache hit

    total_cost_saved_usd DECIMAL(12,8) NOT NULL DEFAULT 0,
    -- Sum of money saved by this cache entry

    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_hit_at         TIMESTAMP WITH TIME ZONE,

    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now() + INTERVAL '24 hours'
    -- Cache entries expire after 24 hours by default
    -- TTL is configurable per request via X-Cache-TTL header
);

-- IVFFlat index for fast approximate nearest-neighbor search
-- This is how semantic cache searches all stored prompts quickly
CREATE INDEX ON semantic_cache
    USING ivfflat (prompt_embedding vector_cosine_ops)
    WITH (lists = 50);
-- lists=50 is appropriate for a few thousand cache entries
-- Increase to 100-200 as cache grows

CREATE INDEX idx_cache_expires ON semantic_cache (expires_at);
-- For cache cleanup job

CREATE INDEX idx_cache_hits ON semantic_cache (hit_count DESC);
-- "most popular cached prompts"
```

### 7.4 Daily Analytics View

```sql
-- migrations/003_analytics.sql

-- Pre-aggregated view for fast dashboard queries
-- Instead of summing millions of rows on every dashboard load,
-- pre-compute daily summaries that can be queried instantly.

CREATE MATERIALIZED VIEW daily_analytics AS
SELECT
    DATE_TRUNC('day', created_at) AS day,
    selected_provider,
    selected_model,
    complexity_tier,
    COUNT(*) AS request_count,
    SUM(total_tokens) AS total_tokens,
    SUM(total_cost_usd) AS total_cost_usd,
    SUM(cost_savings_usd) AS total_savings_usd,
    AVG(total_latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency_ms,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
    SUM(CASE WHEN failover_occurred THEN 1 ELSE 0 END) AS failover_count
FROM requests
GROUP BY 1, 2, 3, 4;

-- Refresh this view on demand (called by scheduler every 5 minutes)
-- In Postgres: REFRESH MATERIALIZED VIEW daily_analytics;
-- The view query runs once, results cached — dashboard queries are instant

CREATE UNIQUE INDEX ON daily_analytics (day, selected_provider, selected_model, complexity_tier);
-- Required for REFRESH MATERIALIZED VIEW CONCURRENTLY (non-blocking refresh)
```

---

### 7.5 request_payloads Table (for Replay)

```sql
-- migrations/004_security.sql

-- Store raw message payloads separately from the main request log.
-- Keeping them separate means you can delete payloads (privacy compliance)
-- without losing the cost/routing analytics in the requests table.

CREATE TABLE request_payloads (
    request_id      UUID PRIMARY KEY REFERENCES requests(request_id) ON DELETE CASCADE,
    -- Foreign key to requests — deleting a request cascades to its payload

    messages        JSONB NOT NULL,
    -- The full messages array as sent by the client
    -- [{"role": "user", "content": "..."}, ...]

    request_params  JSONB NOT NULL DEFAULT '{}',
    -- Other request parameters: max_tokens, temperature, model alias, headers
    -- Stored so replay can reconstruct an identical request

    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_payloads_created ON request_payloads (created_at DESC);

-- Rate limit configuration per client
-- Allows different limits for different clients (dev vs prod keys)
CREATE TABLE rate_limit_config (
    client_id       TEXT PRIMARY KEY,
    -- Matches X-Client-ID header value, or "default" for unconfigured clients

    requests_per_minute  INT NOT NULL DEFAULT 60,
    requests_per_hour    INT NOT NULL DEFAULT 1000,
    requests_per_day     INT NOT NULL DEFAULT 10000,

    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
    -- Hard block — useful if a client is misbehaving

    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Insert default config
INSERT INTO rate_limit_config (client_id, requests_per_minute, requests_per_hour, requests_per_day)
VALUES ('default', 60, 1000, 10000);
```

---

## 8. API Specification

### 8.1 POST /v1/chat/completions — The Core Proxy Endpoint

**Purpose:** OpenAI-compatible chat completion endpoint. Drop-in replacement.

**Request body (OpenAI format):**
```json
{
  "model": "auto",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "max_tokens": 500,
  "temperature": 0.7,
  "stream": false
}
```

**Custom headers (optional):**
```
Authorization: Bearer ng-your-key-here ← REQUIRED — proxy API key (see Section 9.6)
X-Client-ID: my-app-v2          ← tag requests for cost attribution + rate limiting
X-Preferred-Provider: anthropic  ← prefer a specific provider
X-Max-Cost-USD: 0.01            ← refuse to route to models that would cost more than this
X-Force-Tier: mid               ← override routing, use this tier regardless of classifier
X-Cache-TTL: 3600               ← cache TTL in seconds (default: 86400)
X-Skip-Cache: true              ← bypass cache for this request
```

**Special model aliases:**
- `"auto"` — classify and route optimally (default)
- `"cheapest"` — always use cheap tier
- `"balanced"` — always use mid tier
- `"best"` or `"most-capable"` — always use frontier tier
- Any specific model ID from the registry — use that model directly

**Response (OpenAI format — same regardless of which provider ran):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "claude-haiku-4-5",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 9,
    "total_tokens": 33
  },
  "x_neuralgate": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "complexity_score": 0.18,
    "complexity_tier": "cheap",
    "requested_model": "auto",
    "selected_model": "claude-haiku-4-5",
    "selected_provider": "anthropic",
    "cache_hit": false,
    "failover": false,
    "total_cost_usd": 0.0000192,
    "total_latency_ms": 412
  }
}
```

The `x_neuralgate` field is your proxy's metadata — shows routing decision, cost, timing. Clients can inspect it or ignore it.

**Error responses:**

```json
// 400: No available models for the request
{
  "error": {
    "message": "No models available with context window > 180000 tokens",
    "type": "context_window_exceeded",
    "code": 400
  }
}

// 429: All providers rate-limiting
{
  "error": {
    "message": "All providers for mid tier are rate-limiting. Retry after 30s.",
    "type": "all_providers_exhausted",
    "retry_after": 30,
    "code": 429
  }
}

// 503: Provider down and failover exhausted
{
  "error": {
    "message": "Primary provider unavailable, all failover options exhausted",
    "type": "provider_unavailable",
    "code": 503
  }
}
```

---

### 8.2 GET /v1/models — List Available Models

```json
{
  "object": "list",
  "data": [
    {
      "id": "auto",
      "object": "model",
      "description": "Automatically route to optimal model based on complexity"
    },
    {
      "id": "claude-haiku-4-5",
      "object": "model",
      "provider": "anthropic",
      "tier": "cheap",
      "context_window": 200000,
      "input_cost_per_million": 0.80,
      "output_cost_per_million": 4.00
    }
  ]
}
```

---

### 8.3 GET /analytics/summary — Cost Overview

**Query params:** `days` (default 7), `provider` (optional filter), `client_id` (optional filter)

```json
{
  "period_days": 7,
  "total_requests": 15420,
  "total_cost_usd": 12.84,
  "total_savings_usd": 89.31,
  "savings_percent": 87.4,
  "cache_hit_rate": 0.34,
  "tokens_saved_by_cache": 4200000,
  "cost_saved_by_cache_usd": 3.15,
  "failover_rate": 0.002,
  "by_tier": {
    "cheap": {"requests": 9200, "cost_usd": 1.84, "percent": 59.7},
    "mid": {"requests": 5100, "cost_usd": 7.65, "percent": 33.1},
    "frontier": {"requests": 1120, "cost_usd": 3.35, "percent": 7.3}
  },
  "by_provider": {
    "anthropic": {"requests": 8200, "cost_usd": 6.56},
    "openai": {"requests": 5100, "cost_usd": 4.08},
    "google": {"requests": 2120, "cost_usd": 2.20}
  },
  "by_model": [
    {"model": "claude-haiku-4-5", "requests": 7800, "cost_usd": 1.56},
    {"model": "claude-sonnet-4-5", "requests": 4200, "cost_usd": 6.30},
    {"model": "gpt-4o", "requests": 1020, "cost_usd": 3.06}
  ],
  "avg_latency_ms": 687,
  "p95_latency_ms": 2100
}
```

---

### 8.4 GET /analytics/routing — Routing Decision Breakdown

```json
{
  "period_days": 7,
  "complexity_distribution": {
    "cheap": {"count": 9200, "avg_score": 0.21},
    "mid": {"count": 5100, "avg_score": 0.51},
    "frontier": {"count": 1120, "avg_score": 0.78}
  },
  "top_signals": [
    {"signal": "short_prompt", "count": 8400, "avg_score_impact": -0.12},
    {"signal": "keyword:analyze", "count": 1200, "avg_score_impact": 0.15},
    {"signal": "code_detected", "count": 890, "avg_score_impact": 0.15},
    {"signal": "long_conversation", "count": 640, "avg_score_impact": 0.10}
  ],
  "routing_accuracy_proxy": {
    "explanation": "True accuracy requires human evaluation. Proxy: % of cheap-routed requests with finish_reason=stop (not length-truncated)",
    "cheap_complete_rate": 0.97,
    "mid_complete_rate": 0.98,
    "frontier_complete_rate": 0.99
  }
}
```

---

### 8.5 GET /analytics/savings — Cost Savings Analysis

```json
{
  "period_days": 7,
  "actual_cost_usd": 12.84,
  "hypothetical_all_frontier_cost_usd": 102.15,
  "total_savings_usd": 89.31,
  "savings_multiplier": 7.95,
  "explanation": "Intelligent routing cost 7.95x less than sending all requests to frontier models",
  "daily_savings": [
    {"date": "2026-03-01", "actual": 1.84, "hypothetical": 14.60, "savings": 12.76},
    {"date": "2026-03-02", "actual": 1.92, "hypothetical": 15.20, "savings": 13.28}
  ]
}
```

---

### 8.6 GET /analytics/cache — Cache Performance

```json
{
  "period_days": 7,
  "total_requests": 15420,
  "cache_hits": 5243,
  "hit_rate": 0.34,
  "exact_hits": 1200,
  "semantic_hits": 4043,
  "avg_similarity_on_hit": 0.974,
  "tokens_saved": 4200000,
  "cost_saved_usd": 3.15,
  "top_cached_prompts": [
    {
      "prompt_preview": "What is 2+2?",
      "hit_count": 240,
      "cost_saved_usd": 0.018
    }
  ]
}
```

---

### 8.7 GET /health — Health Check

```json
{
  "status": "ok",
  "providers": {
    "anthropic": {"status": "ok", "latency_ms": 450},
    "openai": {"status": "ok", "latency_ms": 380},
    "google": {"status": "degraded", "latency_ms": 1200},
    "deepseek": {"status": "ok", "latency_ms": 890},
    "xai": {"status": "ok", "latency_ms": 520},
    "mistral": {"status": "ok", "latency_ms": 410}
  },
  "cache": {"status": "ok", "entries": 4820},
  "database": {"status": "ok"}
}
```

The health check pings each provider with a minimal request (or just checks connectivity) every 60 seconds. Stores results in Redis with 90s TTL. Used by routing engine to skip unavailable providers.

---

### 8.8 POST /requests/{request_id}/replay — Replay a Request

**Purpose:** Re-run a previously logged request through the proxy. Useful for testing routing changes, verifying failover recovery, or debugging.

**How it works:** Fetches the original messages from `request_payloads`, sends them through the full proxy pipeline as a fresh request (classify → route → call provider → log), and returns both the new response and a comparison with the original.

**Response:**
```json
{
  "original": {
    "request_id": "550e8400-...",
    "selected_model": "claude-haiku-4-5",
    "complexity_tier": "cheap",
    "total_cost_usd": 0.0000048,
    "total_latency_ms": 412,
    "content": "The capital of France is Paris."
  },
  "replayed": {
    "request_id": "661f9511-...",
    "selected_model": "claude-haiku-4-5",
    "complexity_tier": "cheap",
    "total_cost_usd": 0.0000051,
    "total_latency_ms": 389,
    "content": "Paris is the capital of France."
  },
  "diff": {
    "model_changed": false,
    "tier_changed": false,
    "cost_delta_usd": 0.0000003,
    "latency_delta_ms": -23
  }
}
```

**Error if payload not stored:**
```json
{
  "error": {
    "message": "No payload stored for request 550e8400. Enable STORE_PAYLOADS=true to use replay.",
    "type": "payload_not_found",
    "code": 404
  }
}
```

---

### 8.9 GET /rate-limits/{client_id} — View Rate Limit Status

**Purpose:** Check current rate limit usage and config for a client.

```json
{
  "client_id": "my-app",
  "config": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "requests_per_day": 10000
  },
  "current_usage": {
    "this_minute": 12,
    "this_hour": 340,
    "this_day": 1820
  },
  "remaining": {
    "this_minute": 48,
    "this_hour": 660,
    "this_day": 8180
  },
  "is_blocked": false,
  "resets_at": {
    "minute": "2026-03-06T14:23:00Z",
    "hour": "2026-03-06T15:00:00Z",
    "day": "2026-03-07T00:00:00Z"
  }
}
```

---

### 8.10 PUT /rate-limits/{client_id} — Update Rate Limit Config

**Purpose:** Adjust limits per client without restarting the proxy.

**Request body:**
```json
{
  "requests_per_minute": 120,
  "requests_per_hour": 2000,
  "requests_per_day": 20000,
  "is_blocked": false
}
```

**Response:** Updated config object (same shape as GET response).

---

### 9.1 Project Structure and Settings

**`proxy/settings.py`:**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Provider API keys — all optional, only providers with keys are used
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # Embedding model for semantic cache
    # We use OpenAI's embedding model (cheap: $0.02/million tokens)
    # If you only have Anthropic key, you can use a local model instead
    embedding_model: str = "text-embedding-3-small"

    # Semantic cache settings
    cache_similarity_threshold: float = 0.95
    # Prompts with cosine similarity > this are considered cache hits
    # 0.95 is conservative — feels identical to the user
    # Lower to 0.90 for more aggressive caching (slightly more risk of wrong answers)

    default_cache_ttl_hours: int = 24

    # Routing defaults
    default_requested_model: str = "auto"
    max_failover_attempts: int = 3

    class Config:
        env_file = ".env"

settings = Settings()

# Derive which providers are available based on which keys are set
def get_available_providers() -> set[str]:
    available = set()
    if settings.anthropic_api_key:
        available.add("anthropic")
    if settings.openai_api_key:
        available.add("openai")
    if settings.google_api_key:
        available.add("google")
    if settings.xai_api_key:
        available.add("xai")
    if settings.deepseek_api_key:
        available.add("deepseek")
    if settings.mistral_api_key:
        available.add("mistral")
    return available
```

---

### 9.2 Provider Adapters

Each provider has different request/response formats. You need adapters that translate between your internal format and each provider's format.

**`proxy/providers/base.py`:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ProviderResponse:
    """Normalized response — same structure regardless of which provider ran."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    raw_response: dict  # Original provider response, stored for debugging

class BaseProvider(ABC):
    """Every provider adapter implements this interface."""

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> ProviderResponse:
        """Send chat completion request, return normalized response."""
        pass

    @abstractmethod
    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """Convert OpenAI-format messages to provider-specific format."""
        pass

    @abstractmethod
    def parse_response(self, raw: dict) -> ProviderResponse:
        """Convert provider response to normalized ProviderResponse."""
        pass
```

**`proxy/providers/anthropic_provider.py`:**
```python
import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings

class AnthropicProvider(BaseProvider):
    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0  # LLMs can be slow — generous timeout
        )

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """
        OpenAI format → Anthropic format.

        Key differences:
        1. System prompt is a top-level "system" field, not in messages array
        2. Anthropic doesn't use "system" role in messages array
        3. max_tokens is required in Anthropic (optional in OpenAI)
        """
        system = None
        filtered_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
                # Don't add to filtered_messages — Anthropic takes it separately
            else:
                filtered_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        request = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens or 4096,
        }

        if system:
            request["system"] = system

        if temperature is not None:
            request["temperature"] = temperature

        return request

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        Anthropic response → normalized ProviderResponse.

        Anthropic response structure:
        {
            "content": [{"type": "text", "text": "..."}],
            "model": "claude-haiku-4-5-20251001",
            "usage": {"input_tokens": 24, "output_tokens": 9},
            "stop_reason": "end_turn"
        }
        """
        content = ""
        for block in raw.get("content", []):
            if block.get("type") == "text":
                content += block["text"]

        usage = raw.get("usage", {})

        # Map Anthropic stop reasons to OpenAI finish reasons
        stop_reason_map = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
        }

        return ProviderResponse(
            content=content,
            model=raw.get("model", "unknown"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            finish_reason=stop_reason_map.get(raw.get("stop_reason", "end_turn"), "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        response = await self.client.post("/messages", json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
```

**`proxy/providers/openai_provider.py`:**
```python
import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings

class OpenAIProvider(BaseProvider):
    BASE_URL = "https://api.openai.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0
        )

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """
        OpenAI → OpenAI: no translation needed. Just pass through.
        OpenAI natively uses the system/user/assistant message format.
        """
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        OpenAI response structure:
        {
            "choices": [{"message": {"content": "..."}, "finish_reason": "stop"}],
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 24, "completion_tokens": 9}
        }
        """
        choice = raw["choices"][0]
        usage = raw.get("usage", {})

        return ProviderResponse(
            content=choice["message"]["content"],
            model=raw.get("model", "unknown"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        response = await self.client.post("/chat/completions", json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
```

**`proxy/providers/google_provider.py`:**
```python
import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings

class GoogleProvider(BaseProvider):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.api_key = settings.google_api_key

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        """
        OpenAI format → Google Gemini format.

        Key differences:
        1. Messages go in "contents" not "messages"
        2. Content is in "parts" array: [{"text": "..."}]
        3. System prompt goes in "systemInstruction"
        4. Generation config is separate: {"generationConfig": {...}}
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                # Map "assistant" → "model" for Gemini
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        request = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens or 4096,
                "temperature": temperature,
            }
        }

        if system_instruction:
            request["systemInstruction"] = system_instruction

        return request

    def parse_response(self, raw: dict) -> ProviderResponse:
        """
        Google response structure:
        {
            "candidates": [{"content": {"parts": [{"text": "..."}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 24, "candidatesTokenCount": 9}
        }
        """
        candidate = raw["candidates"][0]
        content = ""
        for part in candidate["content"]["parts"]:
            content += part.get("text", "")

        usage = raw.get("usageMetadata", {})

        finish_map = {"STOP": "stop", "MAX_TOKENS": "length"}

        return ProviderResponse(
            content=content,
            model="gemini",
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=finish_map.get(candidate.get("finishReason", "STOP"), "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        # Google uses the model name in the URL, not the request body
        url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"
        response = await self.client.post(url, json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
```

**`proxy/providers/deepseek_provider.py`:**
```python
import httpx
from proxy.providers.base import BaseProvider, ProviderResponse
from proxy.settings import settings

class DeepSeekProvider(BaseProvider):
    """
    DeepSeek uses OpenAI-compatible API format.
    This is the easiest provider to integrate — minimal translation needed.
    """
    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0
        )

    def format_request(self, messages: list[dict], model: str, max_tokens: int, temperature: float) -> dict:
        # OpenAI-compatible — no translation needed
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }

    def parse_response(self, raw: dict) -> ProviderResponse:
        # OpenAI-compatible response format
        choice = raw["choices"][0]
        usage = raw.get("usage", {})
        return ProviderResponse(
            content=choice["message"]["content"],
            model=raw.get("model", "deepseek-chat"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=raw
        )

    async def complete(self, model: str, messages: list[dict], max_tokens: int = 4096,
                       temperature: float = 0.7, **kwargs) -> ProviderResponse:
        request_body = self.format_request(messages, model, max_tokens, temperature)
        response = await self.client.post("/chat/completions", json=request_body)
        response.raise_for_status()
        return self.parse_response(response.json())
```

**Note:** xAI (Grok) and Mistral are also OpenAI-compatible APIs — copy `deepseek_provider.py`, change `BASE_URL` and the API key field. Takes 5 minutes each.

---

### 9.3 Provider Registry

```python
# proxy/providers/__init__.py

from proxy.providers.anthropic_provider import AnthropicProvider
from proxy.providers.openai_provider import OpenAIProvider
from proxy.providers.google_provider import GoogleProvider
from proxy.providers.deepseek_provider import DeepSeekProvider
from proxy.settings import settings, get_available_providers

# Lazy instantiation — only create providers where we have API keys
_providers = {}

def get_provider(provider_name: str):
    if provider_name not in _providers:
        available = get_available_providers()
        if provider_name not in available:
            raise ValueError(f"Provider '{provider_name}' not configured. Add API key to .env")

        if provider_name == "anthropic":
            _providers[provider_name] = AnthropicProvider()
        elif provider_name == "openai":
            _providers[provider_name] = OpenAIProvider()
        elif provider_name == "google":
            _providers[provider_name] = GoogleProvider()
        elif provider_name == "deepseek":
            _providers[provider_name] = DeepSeekProvider()
        # Add xai, mistral similarly (copy deepseek, change base_url + key)

    return _providers[provider_name]
```

---

### 9.4 The Main Proxy Handler

**`proxy/routers/completions.py`:**
```python
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import time
import hashlib
import json
import uuid

from proxy.classifier import classify_complexity, count_tokens
from proxy.router import select_model
from proxy.model_registry import MODEL_REGISTRY
from proxy.providers import get_provider
from proxy.cache import check_semantic_cache, store_semantic_cache
from proxy.cost import calculate_cost, calculate_frontier_cost
from proxy.db import get_db

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[Message]
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

@router.post("/v1/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    request: Request,
    x_client_id: Optional[str] = Header(None),
    x_preferred_provider: Optional[str] = Header(None),
    x_max_cost_usd: Optional[float] = Header(None),
    x_force_tier: Optional[str] = Header(None),
    x_skip_cache: Optional[str] = Header(None),
    x_cache_ttl: Optional[int] = Header(None),
):
    wall_start = time.monotonic()
    request_id = str(uuid.uuid4())

    if request_body.stream:
        raise HTTPException(
            status_code=400,
            detail={"message": "Streaming not supported in v1. Use stream=false.",
                    "type": "streaming_not_supported"}
        )

    messages = [m.dict() for m in request_body.messages]

    # ── Step 1: Token counting ────────────────────────────────────────────
    full_text = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
    prompt_tokens_estimate = count_tokens(full_text)

    # ── Step 2: Messages hash for exact cache lookup ───────────────────────
    messages_json = json.dumps(messages, sort_keys=True)
    messages_hash = hashlib.sha256(messages_json.encode()).hexdigest()

    # ── Step 3: Semantic cache check ──────────────────────────────────────
    cache_result = None
    skip_cache = x_skip_cache and x_skip_cache.lower() == "true"

    if not skip_cache:
        cache_result = await check_semantic_cache(
            messages_hash=messages_hash,
            full_text=full_text,
            db=request.app.state.db_pool,
            redis=request.app.state.redis,
        )

    if cache_result:
        # Cache hit — return immediately
        wall_elapsed = round((time.monotonic() - wall_start) * 1000)

        # Log async (don't await — fire and forget)
        import asyncio
        asyncio.create_task(log_request(
            request_id=request_id,
            requested_model=request_body.model,
            selected_model=cache_result["model"],
            selected_provider="cache",
            prompt_tokens=prompt_tokens_estimate,
            completion_tokens=cache_result["completion_tokens"],
            input_cost_usd=0,
            output_cost_usd=0,
            frontier_cost_usd=0,
            cache_hit=True,
            cache_similarity=cache_result.get("similarity"),
            total_latency_ms=wall_elapsed,
            provider_latency_ms=0,
            complexity_score=None,
            complexity_tier=None,
            complexity_signals=None,
            messages_hash=messages_hash,
            message_count=len(messages),
            finish_reason=cache_result.get("finish_reason", "stop"),
            client_id=x_client_id,
            db=request.app.state.db_pool,
        ))

        return build_response(
            request_id=request_id,
            content=cache_result["content"],
            model=cache_result["model"],
            prompt_tokens=prompt_tokens_estimate,
            completion_tokens=cache_result["completion_tokens"],
            finish_reason=cache_result.get("finish_reason", "stop"),
            complexity_score=None,
            complexity_tier=None,
            requested_model=request_body.model,
            selected_model=cache_result["model"],
            selected_provider="cache",
            cache_hit=True,
            cache_similarity=cache_result.get("similarity"),
            failover=False,
            total_cost_usd=0,
            total_latency_ms=wall_elapsed,
        )

    # ── Step 4: Classify complexity ───────────────────────────────────────
    if x_force_tier:
        complexity_result = {
            "score": 0.5,
            "tier": x_force_tier,
            "signals": [f"forced_tier:{x_force_tier}"],
            "total_tokens": prompt_tokens_estimate,
            "reasoning": f"Tier forced by X-Force-Tier header: {x_force_tier}"
        }
    else:
        complexity_result = classify_complexity(messages)

    # ── Step 5: Select model + failover chain ─────────────────────────────
    selected_model, failover_chain = select_model(
        requested_model=request_body.model,
        complexity_result=complexity_result,
        prompt_tokens=prompt_tokens_estimate,
        preferred_provider=x_preferred_provider,
        max_cost_per_request=x_max_cost_usd,
    )

    # ── Step 6: Call provider with failover ───────────────────────────────
    provider_start = time.monotonic()
    provider_response = None
    actual_model = selected_model
    failover_occurred = False
    original_model = None

    models_to_try = [selected_model] + failover_chain

    for model_id in models_to_try:
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            continue

        provider_name = model_info["provider"]

        try:
            provider = get_provider(provider_name)
            provider_response = await provider.complete(
                model=model_id,
                messages=messages,
                max_tokens=request_body.max_tokens or 4096,
                temperature=request_body.temperature or 0.7,
            )
            actual_model = model_id

            if model_id != selected_model:
                failover_occurred = True
                original_model = selected_model

            break  # Success — stop trying

        except Exception as e:
            error_str = str(e)
            # 429 = rate limit, 5xx = server error → try next model
            if any(code in error_str for code in ["429", "500", "502", "503"]):
                continue
            else:
                # 4xx client error (bad request, invalid model) — don't retry
                raise HTTPException(
                    status_code=400,
                    detail={"message": f"Provider error: {error_str}", "type": "provider_error"}
                )

    if not provider_response:
        raise HTTPException(
            status_code=503,
            detail={"message": "All providers unavailable", "type": "all_providers_exhausted"}
        )

    provider_elapsed = round((time.monotonic() - provider_start) * 1000)
    wall_elapsed = round((time.monotonic() - wall_start) * 1000)

    # ── Step 7: Calculate cost ─────────────────────────────────────────────
    actual_model_info = MODEL_REGISTRY[actual_model]
    input_cost, output_cost = calculate_cost(
        model_info=actual_model_info,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )
    frontier_cost = calculate_frontier_cost(
        tier=complexity_result["tier"],
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )

    # ── Step 8: Store in semantic cache ───────────────────────────────────
    import asyncio
    asyncio.create_task(store_semantic_cache(
        messages_hash=messages_hash,
        full_text=full_text,
        response_content=provider_response.content,
        response_metadata={
            "model": actual_model,
            "finish_reason": provider_response.finish_reason,
            "prompt_tokens": provider_response.prompt_tokens,
            "completion_tokens": provider_response.completion_tokens,
        },
        ttl_hours=x_cache_ttl / 3600 if x_cache_ttl else None,
        db=request.app.state.db_pool,
        redis=request.app.state.redis,
    ))

    # ── Step 9: Log request ───────────────────────────────────────────────
    asyncio.create_task(log_request(
        request_id=request_id,
        requested_model=request_body.model,
        selected_model=actual_model,
        selected_provider=actual_model_info["provider"],
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        frontier_cost_usd=frontier_cost,
        cache_hit=False,
        cache_similarity=None,
        total_latency_ms=wall_elapsed,
        provider_latency_ms=provider_elapsed,
        complexity_score=complexity_result["score"],
        complexity_tier=complexity_result["tier"],
        complexity_signals=complexity_result["signals"],
        messages_hash=messages_hash,
        message_count=len(messages),
        finish_reason=provider_response.finish_reason,
        failover_occurred=failover_occurred,
        original_model=original_model,
        client_id=x_client_id,
        db=request.app.state.db_pool,
    ))

    # ── Step 10: Return response ──────────────────────────────────────────
    return build_response(
        request_id=request_id,
        content=provider_response.content,
        model=actual_model,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
        finish_reason=provider_response.finish_reason,
        complexity_score=complexity_result["score"],
        complexity_tier=complexity_result["tier"],
        requested_model=request_body.model,
        selected_model=actual_model,
        selected_provider=actual_model_info["provider"],
        cache_hit=False,
        cache_similarity=None,
        failover=failover_occurred,
        total_cost_usd=input_cost + output_cost,
        total_latency_ms=wall_elapsed,
    )


def build_response(request_id, content, model, prompt_tokens, completion_tokens,
                   finish_reason, complexity_score, complexity_tier, requested_model,
                   selected_model, selected_provider, cache_hit, cache_similarity,
                   failover, total_cost_usd, total_latency_ms):
    """Build OpenAI-format response with NeuralGate metadata."""
    import time
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": finish_reason
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "x_neuralgate": {
            "request_id": request_id,
            "complexity_score": complexity_score,
            "complexity_tier": complexity_tier,
            "requested_model": requested_model,
            "selected_model": selected_model,
            "selected_provider": selected_provider,
            "cache_hit": cache_hit,
            "cache_similarity": cache_similarity,
            "failover": failover,
            "total_cost_usd": round(total_cost_usd, 8) if total_cost_usd else 0,
            "total_latency_ms": total_latency_ms,
        }
    }


async def log_request(request_id, requested_model, selected_model, selected_provider,
                      prompt_tokens, completion_tokens, input_cost_usd, output_cost_usd,
                      frontier_cost_usd, cache_hit, cache_similarity, total_latency_ms,
                      provider_latency_ms, complexity_score, complexity_tier, complexity_signals,
                      messages_hash, message_count, finish_reason, db,
                      failover_occurred=False, original_model=None, client_id=None):
    """Insert request log record. Called as async background task."""
    import json
    try:
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO requests (
                    request_id, requested_model, selected_model, selected_provider,
                    failover_occurred, original_model,
                    complexity_score, complexity_tier, complexity_signals,
                    prompt_tokens, completion_tokens,
                    input_cost_usd, output_cost_usd, frontier_cost_usd,
                    cache_hit, cache_similarity,
                    total_latency_ms, provider_latency_ms,
                    messages_hash, message_count, finish_reason, client_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
                )
            """,
            request_id, requested_model, selected_model, selected_provider,
            failover_occurred, original_model,
            complexity_score, complexity_tier,
            json.dumps(complexity_signals) if complexity_signals else None,
            prompt_tokens, completion_tokens,
            input_cost_usd, output_cost_usd, frontier_cost_usd,
            cache_hit, cache_similarity,
            total_latency_ms, provider_latency_ms,
            messages_hash, message_count, finish_reason, client_id)
    except Exception as e:
        # Log errors silently — never fail a request because logging failed
        print(f"Log error: {e}")
```

---

### 9.5 Cost Calculation

**`proxy/cost.py`:**
```python
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
    Calculate what this request WOULD have cost on the frontier model for its tier.
    Used to compute cost savings from intelligent routing.

    If a cheap-tier request (complexity=low) was routed to claude-haiku-4-5 but
    the frontier model for cheap tier is also claude-haiku-4-5, savings=0.
    But if a mid-tier request was routed to deepseek-chat (cheap) instead of
    claude-sonnet-4-5 (default mid), we calculate the delta.

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

---

### 9.6 Proxy API Key Authentication

**What it is:** A FastAPI middleware that runs before every request handler. If the `Authorization` header is missing or doesn't match `Bearer {PROXY_API_KEY}`, the request is rejected with 401 before anything else runs — no routing, no LLM calls, zero cost incurred.

**Why middleware and not a dependency:** Middleware runs unconditionally on every request including `/health`. A FastAPI `Depends()` would need to be added to every route individually — easy to forget on a new route. Middleware is a single place that catches everything.

**`proxy/middleware/auth.py`:**
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from proxy.settings import settings

# Routes that don't require authentication
# Health check is public so monitoring systems can check it
PUBLIC_ROUTES = {"/health", "/metrics"}

async def api_key_middleware(request: Request, call_next):
    """
    FastAPI middleware: check Authorization header on every request.

    Usage:
        app.middleware("http")(api_key_middleware)

    Clients must send:
        Authorization: Bearer ng-your-secret-key-here
    """
    # Skip auth for public routes
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    # Skip auth if no proxy key configured (dev mode)
    if not settings.proxy_api_key:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Missing Authorization header. Include: Authorization: Bearer <your-proxy-key>",
                    "type": "authentication_required",
                    "code": 401
                }
            }
        )

    provided_key = auth_header[len("Bearer "):]

    if provided_key != settings.proxy_api_key:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Invalid proxy API key.",
                    "type": "invalid_api_key",
                    "code": 401
                }
            }
        )

    return await call_next(request)
```

**Add to `proxy/settings.py`:**
```python
# Add this field to the Settings class
proxy_api_key: Optional[str] = None
# If not set, auth is disabled (useful for local dev)
# Set in production: PROXY_API_KEY=ng-your-long-random-secret
```

**Add to `.env.example`:**
```bash
# Proxy authentication — set this to protect your proxy
# Generate a key: python3 -c "import secrets; print('ng-' + secrets.token_hex(32))"
PROXY_API_KEY=ng-your-generated-key-here
```

**Register in `proxy/main.py`:**
```python
from proxy.middleware.auth import api_key_middleware

# Add after creating the FastAPI app
app.middleware("http")(api_key_middleware)
```

**Testing auth:**
```bash
# Should return 401
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "test"}]}'

# Should work
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ng-your-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "test"}]}'
```

**What to search if stuck:** "FastAPI middleware example", "FastAPI HTTP middleware authentication"

---

### 9.7 Per-Client Rate Limiting

**What it is:** A Redis-based sliding window counter that caps requests per client per time window. Runs as middleware after auth, before routing. Returns `429 Too Many Requests` with a `Retry-After` header when a client exceeds their limit.

**Why a sliding window and not a fixed window:** A fixed window resets at the top of every minute. A client could send 60 requests at 12:00:59 and 60 more at 12:01:01 — 120 requests in 2 seconds, technically within "1 per second average" but actually a burst that could spike your API costs. A sliding window checks the count over the last 60 seconds from the current moment, smoothing out bursts.

**`proxy/middleware/rate_limit.py`:**
```python
import time
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

PUBLIC_ROUTES = {"/health", "/metrics"}

# Default limits (requests per window)
DEFAULT_LIMITS = {
    "minute": 60,    # 60 requests per 60 seconds
    "hour": 1000,    # 1000 requests per hour
    "day": 10000,    # 10000 requests per day
}

WINDOW_SECONDS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}

async def get_client_limits(client_id: str, db) -> dict:
    """
    Fetch per-client rate limit config from Postgres.
    Falls back to DEFAULT_LIMITS if client not configured.
    """
    try:
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT requests_per_minute, requests_per_hour, requests_per_day, is_blocked "
                "FROM rate_limit_config WHERE client_id = $1 OR client_id = 'default' "
                "ORDER BY client_id = $1 DESC LIMIT 1",
                client_id
            )
            if row:
                if row["is_blocked"]:
                    return None  # Signal: hard blocked
                return {
                    "minute": row["requests_per_minute"],
                    "hour": row["requests_per_hour"],
                    "day": row["requests_per_day"],
                }
    except Exception:
        pass
    return DEFAULT_LIMITS


async def check_rate_limit(
    client_id: str,
    redis: aioredis.Redis,
    db,
) -> tuple[bool, dict]:
    """
    Check if client is within rate limits using Redis sliding window.

    Returns:
        (allowed: bool, info: dict with current counts and limits)
    """
    limits = await get_client_limits(client_id, db)

    if limits is None:
        # Hard blocked client
        return False, {"reason": "client_blocked", "retry_after": 3600}

    now = int(time.time())
    results = {}

    for window_name, limit in limits.items():
        window_secs = WINDOW_SECONDS[window_name]
        redis_key = f"ratelimit:{client_id}:{window_name}"

        # Sliding window: use a sorted set where score = timestamp
        pipe = redis.pipeline()
        # Remove entries older than the window
        pipe.zremrangebyscore(redis_key, 0, now - window_secs)
        # Count remaining entries (requests in this window)
        pipe.zcard(redis_key)
        # Add this request
        pipe.zadd(redis_key, {str(now) + f":{id(pipe)}": now})
        # Set expiry on the key
        pipe.expire(redis_key, window_secs + 1)
        _, count, _, _ = await pipe.execute()

        results[window_name] = {
            "count": count,
            "limit": limit,
            "remaining": max(0, limit - count),
            "resets_at": now + window_secs,
        }

        if count >= limit:
            # Over limit — return which window triggered
            return False, {
                "reason": f"rate_limit_exceeded_{window_name}",
                "retry_after": window_secs,
                "window": window_name,
                "limit": limit,
                "current": count,
                "all_windows": results,
            }

    return True, {"all_windows": results}


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware: enforce per-client rate limits.
    Must run AFTER auth middleware (so we know the client is authenticated).
    """
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    # Determine client identity
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        # Fall back to a hash of the API key — still rate-limited, just not labeled
        auth = request.headers.get("Authorization", "")
        client_id = "anon-" + auth[-8:] if auth else "anon"

    allowed, info = await check_rate_limit(
        client_id=client_id,
        redis=request.app.state.redis,
        db=request.app.state.db_pool,
    )

    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(info.get("retry_after", 60))},
            content={
                "error": {
                    "message": f"Rate limit exceeded. {info.get('reason', '')}",
                    "type": "rate_limit_exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "code": 429,
                    "details": info,
                }
            }
        )

    # Attach rate limit info to request state for logging
    request.state.rate_limit_info = info
    response = await call_next(request)

    # Add rate limit headers to response (same pattern as GitHub's API)
    if hasattr(request.state, "rate_limit_info"):
        minute_info = info.get("all_windows", {}).get("minute", {})
        response.headers["X-RateLimit-Limit"] = str(minute_info.get("limit", 60))
        response.headers["X-RateLimit-Remaining"] = str(minute_info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(minute_info.get("resets_at", 0))

    return response
```

**Register in `proxy/main.py` (order matters — auth runs first, then rate limit):**
```python
from proxy.middleware.auth import api_key_middleware
from proxy.middleware.rate_limit import rate_limit_middleware

app.middleware("http")(rate_limit_middleware)  # runs second
app.middleware("http")(api_key_middleware)     # runs first
# FastAPI middleware stack is LIFO — last registered runs first
```

**Testing rate limits:**
```bash
# Send 65 requests rapidly — 61st+ should return 429
for i in {1..65}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/v1/chat/completions \
    -H "Authorization: Bearer ng-your-key" \
    -H "X-Client-ID: test-client" \
    -H "Content-Type: application/json" \
    -d '{"model":"cheapest","messages":[{"role":"user","content":"hi"}]}')
  echo "Request $i: $STATUS"
done
```

**What to search if stuck:** "Redis sorted set sliding window rate limit", "FastAPI middleware order"

---

### 9.8 Request Replay

**What it is:** Store the raw messages payload for every request (optional, controlled by `STORE_PAYLOADS=true` in `.env`). Expose a `/requests/{id}/replay` endpoint that re-runs the original request through the full proxy pipeline and returns a comparison of original vs replayed result.

**`proxy/routers/replay.py`:**
```python
from fastapi import APIRouter, HTTPException, Request
import json
import uuid
import time

from proxy.classifier import classify_complexity, count_tokens
from proxy.router import select_model
from proxy.model_registry import MODEL_REGISTRY
from proxy.providers import get_provider
from proxy.cost import calculate_cost, calculate_frontier_cost

router = APIRouter()

@router.post("/requests/{request_id}/replay")
async def replay_request(request_id: str, request: Request):
    """
    Re-run a previously logged request through the proxy pipeline.
    Requires STORE_PAYLOADS=true and the original request to have a stored payload.
    """
    db = request.app.state.db_pool

    # Step 1: Fetch original request metadata
    async with db.acquire() as conn:
        original = await conn.fetchrow(
            "SELECT * FROM requests WHERE request_id = $1",
            request_id
        )
        if not original:
            raise HTTPException(status_code=404, detail={
                "message": f"Request {request_id} not found",
                "type": "not_found"
            })

        # Step 2: Fetch stored payload
        payload = await conn.fetchrow(
            "SELECT messages, request_params FROM request_payloads WHERE request_id = $1",
            request_id
        )
        if not payload:
            raise HTTPException(status_code=404, detail={
                "message": f"No payload stored for request {request_id}. "
                           f"Enable STORE_PAYLOADS=true in .env to use replay.",
                "type": "payload_not_found"
            })

    messages = json.loads(payload["messages"])
    params = json.loads(payload["request_params"])

    # Step 3: Re-run through the proxy pipeline
    t0 = time.monotonic()
    full_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    prompt_tokens = count_tokens(full_text)
    complexity = classify_complexity(messages)
    selected_model, failover_chain = select_model(
        requested_model=params.get("model", "auto"),
        complexity_result=complexity,
        prompt_tokens=prompt_tokens,
    )

    # Call provider
    provider_response = None
    actual_model = selected_model
    models_to_try = [selected_model] + failover_chain

    for model_id in models_to_try:
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            continue
        try:
            provider = get_provider(model_info["provider"])
            provider_response = await provider.complete(
                model=model_id,
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7),
            )
            actual_model = model_id
            break
        except Exception:
            continue

    if not provider_response:
        raise HTTPException(status_code=503, detail={
            "message": "All providers unavailable during replay",
            "type": "providers_unavailable"
        })

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    model_info = MODEL_REGISTRY[actual_model]
    input_cost, output_cost = calculate_cost(
        model_info=model_info,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )
    total_cost = input_cost + output_cost

    # Step 4: Log the replayed request (with replayed_from field)
    new_request_id = str(uuid.uuid4())
    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO requests (
                request_id, requested_model, selected_model, selected_provider,
                complexity_score, complexity_tier,
                prompt_tokens, completion_tokens,
                input_cost_usd, output_cost_usd,
                total_latency_ms, messages_hash, message_count,
                finish_reason, cache_hit
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        """,
        new_request_id,
        params.get("model", "auto"), actual_model, model_info["provider"],
        complexity["score"], complexity["tier"],
        provider_response.prompt_tokens, provider_response.completion_tokens,
        input_cost, output_cost,
        elapsed_ms, original["messages_hash"], original["message_count"],
        provider_response.finish_reason, False)

    # Step 5: Return comparison
    return {
        "original": {
            "request_id": request_id,
            "selected_model": original["selected_model"],
            "complexity_tier": original["complexity_tier"],
            "complexity_score": float(original["complexity_score"] or 0),
            "total_cost_usd": float(original["total_cost_usd"] or 0),
            "total_latency_ms": original["total_latency_ms"],
        },
        "replayed": {
            "request_id": new_request_id,
            "selected_model": actual_model,
            "complexity_tier": complexity["tier"],
            "complexity_score": complexity["score"],
            "content": provider_response.content,
            "total_cost_usd": round(total_cost, 8),
            "total_latency_ms": elapsed_ms,
        },
        "diff": {
            "model_changed": original["selected_model"] != actual_model,
            "tier_changed": original["complexity_tier"] != complexity["tier"],
            "cost_delta_usd": round(total_cost - float(original["total_cost_usd"] or 0), 8),
            "latency_delta_ms": elapsed_ms - (original["total_latency_ms"] or 0),
        }
    }
```

**Store payloads in `completions.py` (add after request parsing, before cache check):**
```python
# In the main chat_completions handler, add after Step 1 (token counting):

from proxy.settings import settings

# Step 1.5: Store payload for replay (if enabled)
if settings.store_payloads:
    import asyncio
    asyncio.create_task(_store_payload(
        request_id=request_id,
        messages=messages,
        params={
            "model": request_body.model,
            "max_tokens": request_body.max_tokens,
            "temperature": request_body.temperature,
        },
        db=request.app.state.db_pool,
    ))

async def _store_payload(request_id: str, messages: list, params: dict, db):
    """Store raw request payload for replay. Non-blocking background task."""
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "INSERT INTO request_payloads (request_id, messages, request_params) "
                "VALUES ($1, $2::jsonb, $3::jsonb)",
                request_id,
                json.dumps(messages),
                json.dumps(params)
            )
    except Exception as e:
        print(f"Payload store error: {e}")
```

**Add to `proxy/settings.py`:**
```python
store_payloads: bool = False
# Set STORE_PAYLOADS=true in .env to enable request replay
# Note: stores all message content in Postgres — consider privacy implications
```

**Register router in `proxy/main.py`:**
```python
from proxy.routers.replay import router as replay_router
app.include_router(replay_router)
```

**Add replay button to `LiveRequestFeed.jsx`:**
```jsx
// Add to each row in the table
const [replayResult, setReplayResult] = useState(null);
const [replaying, setReplaying] = useState(null);

const handleReplay = async (requestId) => {
  setReplaying(requestId);
  try {
    const res = await fetch(`/api/requests/${requestId}/replay`, { method: 'POST' });
    const data = await res.json();
    setReplayResult(data);
  } finally {
    setReplaying(null);
  }
};

// In each row's Flags cell:
<button
  onClick={() => handleReplay(r.request_id)}
  disabled={replaying === r.request_id}
  style={{
    padding: '2px 8px', fontSize: 11, borderRadius: 4,
    background: '#f3f4f6', border: '1px solid #e5e7eb',
    cursor: 'pointer'
  }}
>
  {replaying === r.request_id ? '...' : 'Replay'}
</button>

// Show diff modal when replayResult is set
{replayResult && (
  <div style={{
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 100
  }} onClick={() => setReplayResult(null)}>
    <div style={{
      background: '#fff', borderRadius: 8, padding: 24,
      maxWidth: 500, width: '90%'
    }} onClick={e => e.stopPropagation()}>
      <h3 style={{ margin: '0 0 16px' }}>Replay Comparison</h3>
      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
            <th style={{ textAlign: 'left', padding: '4px 8px' }}></th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Original</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Replayed</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['Model', replayResult.original.selected_model, replayResult.replayed.selected_model],
            ['Tier', replayResult.original.complexity_tier, replayResult.replayed.complexity_tier],
            ['Cost', `$${replayResult.original.total_cost_usd.toFixed(7)}`, `$${replayResult.replayed.total_cost_usd.toFixed(7)}`],
            ['Latency', `${replayResult.original.total_latency_ms}ms`, `${replayResult.replayed.total_latency_ms}ms`],
          ].map(([label, orig, replay]) => (
            <tr key={label} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '6px 8px', color: '#6b7280' }}>{label}</td>
              <td style={{ padding: '6px 8px', textAlign: 'right' }}>{orig}</td>
              <td style={{
                padding: '6px 8px', textAlign: 'right',
                color: orig !== replay ? '#dc2626' : 'inherit',
                fontWeight: orig !== replay ? 600 : 400
              }}>{replay}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Response</div>
        <div style={{
          background: '#f9fafb', borderRadius: 4, padding: 12,
          fontSize: 13, maxHeight: 120, overflow: 'auto'
        }}>
          {replayResult.replayed.content}
        </div>
      </div>
      <button
        onClick={() => setReplayResult(null)}
        style={{ marginTop: 16, padding: '6px 16px', cursor: 'pointer' }}
      >
        Close
      </button>
    </div>
  </div>
)}
```

**What to search if stuck:** "FastAPI POST endpoint with path parameter", "React modal state management"
```

---

## 10. Caching Layer

### 10.1 Two-Level Cache Strategy

**Level 1 — Exact match (Redis GET/SET):**
Hash the messages array with SHA-256. Check Redis. If hit, return instantly. This handles identical repeated requests with zero embedding overhead.

**Level 2 — Semantic match (pgvector similarity):**
If exact miss, embed the prompt and search pgvector for similar cached prompts. If cosine similarity > 0.95, return the cached response.

**`proxy/cache.py`:**
```python
import hashlib
import json
import time
from openai import AsyncOpenAI
from proxy.settings import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_text(text: str) -> list[float]:
    """
    Generate embedding for semantic cache lookup.

    We use OpenAI text-embedding-3-small because:
    - Tiny cost: $0.02 per million tokens (semantic cache queries are short)
    - 1536 dimensions: good quality for similarity search
    - Fast: ~100ms per request

    Alternative if you only have Anthropic key: use a local model like
    sentence-transformers/all-MiniLM-L6-v2 (runs on CPU, free).
    What to search: "sentence-transformers python local embedding"
    """
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]  # Truncate very long prompts for embedding (8k char limit)
    )
    return response.data[0].embedding


async def check_semantic_cache(
    messages_hash: str,
    full_text: str,
    db,
    redis,
) -> dict | None:
    """
    Check both exact and semantic cache. Returns cached response dict or None.
    """
    # ── Level 1: Exact match ──────────────────────────────────────────────
    exact_key = f"cache:exact:{messages_hash}"
    exact_cached = await redis.get(exact_key)
    if exact_cached:
        cached = json.loads(exact_cached)
        # Async update hit tracking (fire and forget)
        import asyncio
        asyncio.create_task(_update_hit_stats(messages_hash, db))
        return {**cached, "similarity": 1.0, "cache_type": "exact"}

    # ── Level 2: Semantic match ───────────────────────────────────────────
    try:
        prompt_embedding = await embed_text(full_text)
    except Exception:
        return None  # If embedding fails, just miss the cache

    # Search pgvector for similar cached prompts
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                cache_id,
                messages_hash,
                response_text,
                response_metadata,
                1 - (prompt_embedding <=> $1::vector) AS similarity
            FROM semantic_cache
            WHERE expires_at > now()
              AND 1 - (prompt_embedding <=> $1::vector) >= $2
            ORDER BY prompt_embedding <=> $1::vector
            LIMIT 1
        """, str(prompt_embedding), settings.cache_similarity_threshold)

    if not row:
        return None

    similarity = float(row["similarity"])
    metadata = row["response_metadata"]

    # Also store in Redis exact cache for fast future lookups
    cache_data = {
        "content": row["response_text"],
        "model": metadata.get("model", "cached"),
        "completion_tokens": metadata.get("completion_tokens", 0),
        "finish_reason": metadata.get("finish_reason", "stop"),
        "cache_type": "semantic",
        "similarity": similarity
    }
    await redis.setex(
        f"cache:exact:{messages_hash}",
        3600,  # 1 hour for this exact prompt
        json.dumps(cache_data)
    )

    # Update hit stats
    import asyncio
    asyncio.create_task(_update_hit_stats(row["messages_hash"], db))

    return cache_data


async def store_semantic_cache(
    messages_hash: str,
    full_text: str,
    response_content: str,
    response_metadata: dict,
    db,
    redis,
    ttl_hours: float | None = None,
):
    """
    Store a prompt+response in the semantic cache.
    Called asynchronously after every successful LLM response.
    """
    ttl = ttl_hours or settings.default_cache_ttl_hours

    try:
        prompt_embedding = await embed_text(full_text)
    except Exception:
        return  # Cache storage failure is non-fatal

    cache_data = {
        "content": response_content,
        "model": response_metadata.get("model", "unknown"),
        "completion_tokens": response_metadata.get("completion_tokens", 0),
        "finish_reason": response_metadata.get("finish_reason", "stop"),
    }

    # Store in pgvector for semantic search
    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO semantic_cache
                (messages_hash, prompt_text, prompt_embedding, response_text,
                 response_metadata, expires_at)
            VALUES ($1, $2, $3::vector, $4, $5::jsonb, now() + $6 * interval '1 hour')
            ON CONFLICT (messages_hash) DO UPDATE
                SET response_text = EXCLUDED.response_text,
                    response_metadata = EXCLUDED.response_metadata,
                    expires_at = EXCLUDED.expires_at,
                    hit_count = semantic_cache.hit_count
        """,
        messages_hash,
        full_text[:5000],   # Truncate very long prompts for storage
        str(prompt_embedding),
        response_content,
        json.dumps(response_metadata),
        ttl)

    # Also store in Redis for fast exact lookups
    await redis.setex(
        f"cache:exact:{messages_hash}",
        int(ttl * 3600),
        json.dumps(cache_data)
    )


async def _update_hit_stats(messages_hash: str, db):
    """Increment hit counter for a cache entry."""
    try:
        async with db.acquire() as conn:
            await conn.execute("""
                UPDATE semantic_cache
                SET hit_count = hit_count + 1, last_hit_at = now()
                WHERE messages_hash = $1
            """, messages_hash)
    except Exception:
        pass
```

---

## 11. Observability

### 11.1 Prometheus Metrics

**`proxy/metrics.py`:**
```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

# ── Counters ──────────────────────────────────────────────────────────────────

requests_total = Counter(
    "neuralgate_requests_total",
    "Total requests processed",
    ["model", "provider", "tier", "cache_hit"]
)

cache_hits_total = Counter(
    "neuralgate_cache_hits_total",
    "Total semantic cache hits",
    ["cache_type"]  # "exact" or "semantic"
)

failovers_total = Counter(
    "neuralgate_failovers_total",
    "Total provider failover events",
    ["from_model", "to_model"]
)

tokens_total = Counter(
    "neuralgate_tokens_total",
    "Total tokens processed",
    ["type", "provider"]  # type: "prompt" or "completion"
)

cost_usd_total = Counter(
    "neuralgate_cost_usd_total",
    "Total cost in USD",
    ["provider", "model"]
)

savings_usd_total = Counter(
    "neuralgate_savings_usd_total",
    "Total cost savings from intelligent routing vs always-frontier"
)

# ── Gauges ────────────────────────────────────────────────────────────────────

cache_entries = Gauge(
    "neuralgate_cache_entries",
    "Current number of entries in semantic cache"
)

cache_hit_rate_1h = Gauge(
    "neuralgate_cache_hit_rate_1h",
    "Cache hit rate over the last hour (0.0 to 1.0)"
)

# ── Histograms ────────────────────────────────────────────────────────────────

request_latency_seconds = Histogram(
    "neuralgate_request_latency_seconds",
    "End-to-end request latency",
    ["model", "tier"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

provider_latency_seconds = Histogram(
    "neuralgate_provider_latency_seconds",
    "Provider API call latency",
    ["provider"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

complexity_score_histogram = Histogram(
    "neuralgate_complexity_score",
    "Distribution of complexity scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

@router.get("/metrics")
async def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 11.2 React Dashboard Components — Full Implementations

**`dashboard/src/api.js`:**
```javascript
const BASE = '/api';

export const getSummary = (days = 7) =>
  fetch(`${BASE}/analytics/summary?days=${days}`).then(r => r.json());

export const getRouting = (days = 7) =>
  fetch(`${BASE}/analytics/routing?days=${days}`).then(r => r.json());

export const getSavings = (days = 7) =>
  fetch(`${BASE}/analytics/savings?days=${days}`).then(r => r.json());

export const getCacheStats = (days = 7) =>
  fetch(`${BASE}/analytics/cache?days=${days}`).then(r => r.json());

export const getRecentRequests = (limit = 20) =>
  fetch(`${BASE}/analytics/recent?limit=${limit}`).then(r => r.json());

export const getHealth = () =>
  fetch(`${BASE}/health`).then(r => r.json());
```

---

**`dashboard/src/components/CostOverview.jsx`** — Summary stat cards:
```jsx
import { useState, useEffect } from 'react';
import { getSummary } from '../api';

const StatCard = ({ label, value, sub, color = '#111' }) => (
  <div style={{
    background: '#fff', borderRadius: 8, padding: '20px 24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)', flex: 1
  }}>
    <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>{sub}</div>}
  </div>
);

export function CostOverview() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getSummary(7).then(setData);
    const interval = setInterval(() => getSummary(7).then(setData), 15000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div style={{ padding: 24, color: '#6b7280' }}>Loading...</div>;

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <StatCard
        label="7-Day Spend"
        value={`$${(data.total_cost_usd || 0).toFixed(4)}`}
        sub={`${data.total_requests?.toLocaleString()} requests`}
      />
      <StatCard
        label="Cost Saved vs All-Frontier"
        value={`$${(data.total_savings_usd || 0).toFixed(4)}`}
        sub={`${data.savings_percent || 0}% cheaper`}
        color="#16a34a"
      />
      <StatCard
        label="Cache Hit Rate"
        value={`${((data.cache_hit_rate || 0) * 100).toFixed(1)}%`}
        sub={`${(data.tokens_saved_by_cache || 0).toLocaleString()} tokens saved`}
        color="#2563eb"
      />
      <StatCard
        label="P95 Latency"
        value={`${data.p95_latency_ms || 0}ms`}
        sub={`avg ${data.avg_latency_ms || 0}ms`}
      />
    </div>
  );
}
```

---

**`dashboard/src/components/SavingsChart.jsx`** — Actual vs all-frontier cost over time:
```jsx
import { useState, useEffect } from 'react';
import { getSavings } from '../api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

export function SavingsChart() {
  const [data, setData] = useState([]);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    getSavings(7).then(d => {
      setData(d.daily_savings || []);
      setMeta(d);
    });
  }, []);

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0 }}>Cost: Actual vs All-Frontier</h3>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            Dashed red = cost if every request went to frontier model
          </p>
        </div>
        {meta && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#16a34a' }}>
              {meta.savings_multiplier?.toFixed(1)}x cheaper
            </div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>vs all-frontier</div>
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }}
                 tickFormatter={d => d?.slice(5)} />
          <YAxis tickFormatter={v => `$${v.toFixed(3)}`} tick={{ fontSize: 11 }} width={60} />
          <Tooltip formatter={(v, n) => [`$${Number(v).toFixed(5)}`, n]} />
          <Legend />
          <Line type="monotone" dataKey="hypothetical" stroke="#ef4444"
                strokeDasharray="5 5" name="If all-frontier" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="actual" stroke="#22c55e"
                strokeWidth={2.5} name="Actual cost" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

**`dashboard/src/components/RoutingChart.jsx`** — Pie chart of requests by tier:
```jsx
import { useState, useEffect } from 'react';
import { getSummary } from '../api';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const TIER_COLORS = { cheap: '#22c55e', mid: '#3b82f6', frontier: '#f59e0b' };
const TIER_LABELS = { cheap: 'Cheap', mid: 'Mid', frontier: 'Frontier' };

export function RoutingChart() {
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    getSummary(7).then(d => {
      const tiers = d.by_tier || {};
      const total = Object.values(tiers).reduce((s, t) => s + (t.requests || 0), 0);
      setChartData(
        Object.entries(tiers).map(([tier, info]) => ({
          name: TIER_LABELS[tier] || tier,
          value: info.requests || 0,
          pct: total > 0 ? ((info.requests / total) * 100).toFixed(1) : 0,
          cost: info.cost_usd || 0,
          color: TIER_COLORS[tier] || '#6b7280',
        }))
      );
    });
  }, []);

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{ background: '#fff', border: '1px solid #e5e7eb',
                    borderRadius: 6, padding: '8px 12px', fontSize: 13 }}>
        <div style={{ fontWeight: 600 }}>{d.name} tier</div>
        <div>{d.value.toLocaleString()} requests ({d.pct}%)</div>
        <div style={{ color: '#6b7280' }}>Cost: ${d.cost.toFixed(4)}</div>
      </div>
    );
  };

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ margin: '0 0 4px' }}>Routing Distribution</h3>
      <p style={{ margin: '0 0 12px', color: '#6b7280', fontSize: 13 }}>
        % of requests routed to each model tier
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={chartData} cx="50%" cy="50%" innerRadius={55}
               outerRadius={85} dataKey="value" paddingAngle={3}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={(v, e) => `${v} (${e.payload.pct}%)`} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

**`dashboard/src/components/ModelBreakdown.jsx`** — Bar chart of cost by model:
```jsx
import { useState, useEffect } from 'react';
import { getSummary } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';

const MODEL_COLORS = {
  'claude-haiku': '#22c55e', 'claude-sonnet': '#3b82f6', 'claude-opus': '#f59e0b',
  'gpt-4o-mini': '#10b981', 'gpt-4o': '#6366f1', 'gemini': '#ec4899',
  'deepseek': '#14b8a6', 'grok': '#f97316', 'mistral': '#8b5cf6',
};

function colorForModel(modelId) {
  for (const [key, color] of Object.entries(MODEL_COLORS)) {
    if (modelId.includes(key)) return color;
  }
  return '#6b7280';
}

export function ModelBreakdown() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getSummary(7).then(d => {
      setData((d.by_model || []).map(m => ({
        name: m.model.replace('claude-', '').replace('-latest', ''),
        full_name: m.model,
        requests: m.requests,
        cost: m.cost_usd,
        color: colorForModel(m.model),
      })));
    });
  }, []);

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ margin: '0 0 4px' }}>Cost by Model</h3>
      <p style={{ margin: '0 0 12px', color: '#6b7280', fontSize: 13 }}>
        7-day spend per model
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical"
                  margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
          <XAxis type="number" tickFormatter={v => `$${v.toFixed(4)}`}
                 tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
          <Tooltip
            formatter={(v, n, p) => [
              `$${Number(v).toFixed(5)} (${p.payload.requests} reqs)`,
              'Cost'
            ]}
          />
          <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

**`dashboard/src/components/LiveRequestFeed.jsx`** — Last 20 requests table:
```jsx
import { useState, useEffect } from 'react';
import { getRecentRequests } from '../api';

const TIER_COLORS = {
  cheap: { bg: '#dcfce7', text: '#15803d' },
  mid: { bg: '#dbeafe', text: '#1d4ed8' },
  frontier: { bg: '#fef9c3', text: '#854d0e' },
};

const Badge = ({ label, bg, text }) => (
  <span style={{
    background: bg, color: text, borderRadius: 4,
    padding: '1px 6px', fontSize: 11, fontWeight: 600
  }}>{label}</span>
);

export function LiveRequestFeed() {
  const [requests, setRequests] = useState([]);

  useEffect(() => {
    const load = () => getRecentRequests(20).then(d => setRequests(d.requests || []));
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ margin: '0 0 16px' }}>Live Request Feed</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
              {['Model', 'Tier', 'Score', 'Tokens', 'Cost', 'Latency', 'Flags'].map(h => (
                <th key={h} style={{ padding: '8px 10px', textAlign: 'left',
                                     color: '#6b7280', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {requests.map((r, i) => {
              const tierStyle = TIER_COLORS[r.complexity_tier] || { bg: '#f3f4f6', text: '#374151' };
              return (
                <tr key={i} style={{
                  borderBottom: '1px solid #f9fafb',
                  background: i % 2 === 0 ? '#fff' : '#fafafa'
                }}>
                  <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontSize: 12 }}>
                    {r.selected_model?.replace('claude-', 'c-').replace('-latest', '')}
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    {r.complexity_tier && (
                      <Badge label={r.complexity_tier} bg={tierStyle.bg} text={tierStyle.text} />
                    )}
                  </td>
                  <td style={{ padding: '8px 10px', color: '#374151' }}>
                    {r.complexity_score?.toFixed(2) ?? '—'}
                  </td>
                  <td style={{ padding: '8px 10px', color: '#374151' }}>
                    {r.total_tokens?.toLocaleString() ?? '—'}
                  </td>
                  <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontSize: 12 }}>
                    ${Number(r.total_cost_usd || 0).toFixed(6)}
                  </td>
                  <td style={{ padding: '8px 10px', color: '#374151' }}>
                    {r.total_latency_ms}ms
                  </td>
                  <td style={{ padding: '8px 10px', display: 'flex', gap: 4 }}>
                    {r.cache_hit && <Badge label="cache" bg="#dcfce7" text="#15803d" />}
                    {r.failover_occurred && <Badge label="failover" bg="#fff7ed" text="#c2410c" />}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {requests.length === 0 && (
          <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>
            No requests yet — send some traffic to the proxy
          </div>
        )}
      </div>
    </div>
  );
}
```

---

**`dashboard/src/components/CachePerformance.jsx`** — Cache hit rate and savings:
```jsx
import { useState, useEffect } from 'react';
import { getCacheStats } from '../api';

export function CachePerformance() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getCacheStats(7).then(setData);
  }, []);

  if (!data) return null;

  const hitRate = ((data.hit_rate || 0) * 100).toFixed(1);
  const exactRate = data.total_requests > 0
    ? ((data.exact_hits / data.total_requests) * 100).toFixed(1) : 0;
  const semanticRate = data.total_requests > 0
    ? ((data.semantic_hits / data.total_requests) * 100).toFixed(1) : 0;

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ margin: '0 0 16px' }}>Semantic Cache Performance</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div style={{ background: '#f0fdf4', borderRadius: 6, padding: 16 }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Overall Hit Rate</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#16a34a' }}>{hitRate}%</div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>{data.cache_hits?.toLocaleString()} hits</div>
        </div>
        <div style={{ background: '#eff6ff', borderRadius: 6, padding: 16 }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Cost Saved by Cache</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#2563eb' }}>
            ${(data.cost_saved_usd || 0).toFixed(4)}
          </div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>
            {(data.tokens_saved || 0).toLocaleString()} tokens
          </div>
        </div>
      </div>
      <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
        <div style={{ flex: 1, background: '#f9fafb', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Exact matches</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{exactRate}%</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>SHA-256 Redis hit</div>
        </div>
        <div style={{ flex: 1, background: '#f9fafb', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Semantic matches</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{semanticRate}%</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>
            avg {(data.avg_similarity_on_hit * 100 || 0).toFixed(1)}% similarity
          </div>
        </div>
        <div style={{ flex: 1, background: '#f9fafb', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Cache entries</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{data.cache_entries?.toLocaleString() || '—'}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>active (24h TTL)</div>
        </div>
      </div>
    </div>
  );
}
```

---

**`dashboard/src/App.jsx`** — Wire everything together:
```jsx
import { CostOverview } from './components/CostOverview';
import { SavingsChart } from './components/SavingsChart';
import { RoutingChart } from './components/RoutingChart';
import { ModelBreakdown } from './components/ModelBreakdown';
import { LiveRequestFeed } from './components/LiveRequestFeed';
import { CachePerformance } from './components/CachePerformance';

export default function App() {
  return (
    <div style={{
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#f9fafb', minHeight: '100vh',
      padding: 24
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>NeuralGate</h1>
          <p style={{ margin: '4px 0 0', color: '#6b7280' }}>
            Intelligent LLM cost-optimization proxy
          </p>
        </div>

        {/* Top summary cards */}
        <CostOverview />

        {/* Main charts row */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
          <SavingsChart />
          <RoutingChart />
        </div>

        {/* Second row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
          <ModelBreakdown />
          <CachePerformance />
        </div>

        {/* Live feed */}
        <div style={{ marginTop: 16 }}>
          <LiveRequestFeed />
        </div>
      </div>
    </div>
  );
}
```

---

**Missing backend endpoint — add to `proxy/routers/analytics.py`:**

```python
# GET /analytics/recent — used by LiveRequestFeed
@router.get("/recent")
async def get_recent_requests(request, limit: int = Query(default=20, ge=1, le=100)):
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                request_id, selected_model, selected_provider,
                complexity_tier, complexity_score,
                prompt_tokens, completion_tokens, total_tokens,
                total_cost_usd, total_latency_ms,
                cache_hit, failover_occurred,
                finish_reason, created_at
            FROM requests
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

    return {
        "requests": [
            {
                "request_id": str(r["request_id"]),
                "selected_model": r["selected_model"],
                "selected_provider": r["selected_provider"],
                "complexity_tier": r["complexity_tier"],
                "complexity_score": float(r["complexity_score"]) if r["complexity_score"] else None,
                "prompt_tokens": r["prompt_tokens"],
                "completion_tokens": r["completion_tokens"],
                "total_tokens": r["total_tokens"],
                "total_cost_usd": float(r["total_cost_usd"]) if r["total_cost_usd"] else 0,
                "total_latency_ms": r["total_latency_ms"],
                "cache_hit": r["cache_hit"],
                "failover_occurred": r["failover_occurred"],
                "finish_reason": r["finish_reason"],
            }
            for r in rows
        ]
    }


# GET /analytics/savings — used by SavingsChart
@router.get("/savings")
async def get_savings(request, days: int = Query(default=7, ge=1, le=90)):
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                DATE_TRUNC('day', created_at)::date AS day,
                SUM(total_cost_usd) AS actual,
                SUM(COALESCE(frontier_cost_usd, total_cost_usd)) AS hypothetical,
                SUM(cost_savings_usd) AS savings
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY 1
            ORDER BY 1
        """, str(days))

        totals = await conn.fetchrow("""
            SELECT
                SUM(total_cost_usd) AS actual,
                SUM(COALESCE(frontier_cost_usd, total_cost_usd)) AS hypothetical
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

    actual = float(totals["actual"] or 0)
    hypothetical = float(totals["hypothetical"] or 0)
    savings = hypothetical - actual

    return {
        "period_days": days,
        "actual_cost_usd": round(actual, 6),
        "hypothetical_all_frontier_cost_usd": round(hypothetical, 6),
        "total_savings_usd": round(savings, 6),
        "savings_multiplier": round(hypothetical / actual, 2) if actual > 0 else 0,
        "daily_savings": [
            {
                "date": str(r["day"]),
                "actual": round(float(r["actual"] or 0), 6),
                "hypothetical": round(float(r["hypothetical"] or 0), 6),
                "savings": round(float(r["savings"] or 0), 6),
            }
            for r in rows
        ]
    }
```

---

**Missing file — `proxy/routers/health.py`:**
```python
from fastapi import APIRouter, Request
import asyncio
import httpx
import time

router = APIRouter()

PROVIDER_HEALTH_ENDPOINTS = {
    "anthropic": ("https://api.anthropic.com", "anthropic_api_key"),
    "openai": ("https://api.openai.com", "openai_api_key"),
    "google": ("https://generativelanguage.googleapis.com", "google_api_key"),
    "deepseek": ("https://api.deepseek.com", "deepseek_api_key"),
    "xai": ("https://api.x.ai", "xai_api_key"),
    "mistral": ("https://api.mistral.ai", "mistral_api_key"),
}

async def check_provider(name: str, base_url: str) -> dict:
    """Quick connectivity check — just verify the host is reachable."""
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(base_url)
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "unreachable", "latency_ms": latency}

@router.get("/health")
async def health(request: Request):
    from proxy.settings import get_available_providers
    available = get_available_providers()

    # Check all available providers concurrently
    checks = {
        name: check_provider(name, url)
        for name, (url, key) in PROVIDER_HEALTH_ENDPOINTS.items()
        if name in available
    }
    results = await asyncio.gather(*checks.values(), return_exceptions=True)
    provider_health = dict(zip(checks.keys(), results))

    # Check Redis
    redis_status = "ok"
    try:
        await request.app.state.redis.ping()
    except Exception:
        redis_status = "unreachable"

    # Check Postgres
    db_status = "ok"
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "unreachable"

    # Cache entry count
    cache_entries = 0
    try:
        async with request.app.state.db_pool.acquire() as conn:
            cache_entries = await conn.fetchval(
                "SELECT COUNT(*) FROM semantic_cache WHERE expires_at > now()"
            )
    except Exception:
        pass

    overall = "ok"
    if db_status != "ok":
        overall = "degraded"
    if any(v.get("status") != "ok" for v in provider_health.values() if isinstance(v, dict)):
        overall = "degraded"

    return {
        "status": overall,
        "providers": {
            name: (result if isinstance(result, dict) else {"status": "error"})
            for name, result in provider_health.items()
        },
        "cache": {"status": "ok", "entries": cache_entries},
        "database": {"status": db_status},
        "redis": {"status": redis_status},
    }
```

---

## 12. Complete File Architecture

```
neuralgate/
│
├── .env                            # API keys and secrets (GITIGNORED)
├── .env.example                    # Template without real keys
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── migrations/
│   ├── 001_requests.sql            # Request log table + indexes
│   ├── 002_cache.sql               # Semantic cache table + pgvector index
│   ├── 003_analytics.sql           # Materialized view for fast analytics
│   └── 004_security.sql            # request_payloads + rate_limit_config tables
│
├── proxy/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app factory + lifespan
│   ├── settings.py                 # Pydantic settings + available providers
│   ├── model_registry.py           # All models, pricing, tier config
│   ├── classifier.py               # classify_complexity() + count_tokens()
│   ├── router.py                   # select_model() + failover chain building
│   ├── cost.py                     # calculate_cost() + calculate_frontier_cost()
│   ├── cache.py                    # check_semantic_cache() + store_semantic_cache()
│   ├── db.py                       # asyncpg pool factory + get_db dependency
│   ├── metrics.py                  # Prometheus metrics + /metrics endpoint
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Bearer token API key check (runs first)
│   │   └── rate_limit.py           # Per-client Redis sliding window limiter
│   └── routers/
│       ├── __init__.py
│       ├── completions.py          # POST /v1/chat/completions (main handler)
│       ├── models.py               # GET /v1/models
│       ├── analytics.py            # GET /analytics/* endpoints
│       ├── replay.py               # POST /requests/{id}/replay
│       ├── rate_limits.py          # GET/PUT /rate-limits/{client_id}
│       └── health.py               # GET /health
│   └── providers/
│       ├── __init__.py             # get_provider() factory
│       ├── base.py                 # BaseProvider ABC + ProviderResponse dataclass
│       ├── anthropic_provider.py   # Anthropic adapter
│       ├── openai_provider.py      # OpenAI adapter
│       ├── google_provider.py      # Google Gemini adapter
│       ├── deepseek_provider.py    # DeepSeek adapter (OpenAI-compatible)
│       ├── xai_provider.py         # xAI Grok adapter (OpenAI-compatible)
│       └── mistral_provider.py     # Mistral adapter (OpenAI-compatible)
│
├── dashboard/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js                  # Fetch wrappers for all endpoints
│       └── components/
│           ├── CostOverview.jsx        # Summary cards
│           ├── RoutingChart.jsx        # Pie: requests by tier
│           ├── ModelBreakdown.jsx      # Bar: cost by model
│           ├── SavingsChart.jsx        # Line: actual vs hypothetical cost
│           ├── CachePerformance.jsx    # Cache hit rate + tokens saved
│           ├── LiveRequestFeed.jsx     # Last 20 requests table
│           └── ComplexityDistribution.jsx  # Histogram of complexity scores
│
├── prometheus/
│   └── prometheus.yml
│
├── load-test/
│   ├── requirements.txt            # httpx asyncio
│   ├── benchmark.py                # Send N requests, measure throughput + latency
│   └── test_prompts.py             # 50 test prompts across difficulty levels
│
└── scripts/
    ├── setup.sh
    └── reset_data.sh               # TRUNCATE all tables, FLUSHALL Redis
```

---

## 13. Docker Compose — Full Configuration

```yaml
version: "3.9"

services:

  postgres:
    image: pgvector/pgvector:pg16
    # MUST use pgvector image — needed for semantic cache vector search
    environment:
      POSTGRES_DB: neuralgate
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d neuralgate"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 15s

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  proxy:
    build: ./proxy
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/neuralgate
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      XAI_API_KEY: ${XAI_API_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      MISTRAL_API_KEY: ${MISTRAL_API_KEY}
      CACHE_SIMILARITY_THRESHOLD: "0.95"
      DEFAULT_CACHE_TTL_HOURS: "24"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - proxy

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheusdata:/prometheus
    depends_on:
      - proxy

volumes:
  pgdata:
  redisdata:
  prometheusdata:
```

**`proxy/Dockerfile`:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`proxy/requirements.txt`:**
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
asyncpg==0.29.0
redis[asyncio]==5.0.1
pydantic-settings==2.1.0
prometheus-client==0.19.0
openai==1.12.0
httpx==0.26.0
tiktoken==0.5.2
python-dotenv==1.0.0
```

**`.env.example`:**
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neuralgate

# Redis
REDIS_URL=redis://localhost:6379

# Provider API Keys (add the ones you have — others will be disabled)
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_API_KEY=your-google-key-here
XAI_API_KEY=xai-your-key-here
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
MISTRAL_API_KEY=your-mistral-key-here

# Cache settings
CACHE_SIMILARITY_THRESHOLD=0.95
DEFAULT_CACHE_TTL_HOURS=24
```

**`proxy/main.py`:**
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import asyncpg
import redis.asyncio as aioredis
from proxy.settings import settings
from proxy.routers import completions, models, analytics, health
from proxy.metrics import router as metrics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20
    )
    app.state.redis = await aioredis.from_url(
        settings.redis_url,
        decode_responses=True
    )
    yield
    # Shutdown
    await app.state.db_pool.close()
    await app.state.redis.close()

app = FastAPI(
    title="NeuralGate",
    description="Intelligent LLM cost-optimization proxy",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(completions.router)
app.include_router(models.router)
app.include_router(analytics.router, prefix="/analytics")
app.include_router(health.router)
app.include_router(metrics_router)
```

---

## 14. Day-by-Day Implementation Guide

> Each day: Goal, Prerequisites, numbered Steps, what to verify at end.

---

### Before Day 1 — Environment Setup

**Step 0.1 — Get API keys**
- Anthropic: console.anthropic.com (required for Day 3)
- OpenAI: platform.openai.com (required for semantic cache embedding + GPT models)
- DeepSeek: platform.deepseek.com (very cheap, good for testing multiple providers)
- Others: optional, add as you go

**Step 0.2 — Create project:**
```bash
mkdir neuralgate && cd neuralgate
git init
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".venv/" >> .gitignore

cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neuralgate
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
DEEPSEEK_API_KEY=your-key
CACHE_SIMILARITY_THRESHOLD=0.95
DEFAULT_CACHE_TTL_HOURS=24
EOF

python3 -m venv .venv
source .venv/bin/activate
```

**Step 0.3 — Read Sections 3, 4, and 5 in full.** The concepts in Section 3 are the entire interview story. Don't skip them.

---

### Day 1 — Foundation: Database + Model Registry

**Goal:** Database is running with schema. Model registry is complete. You can query it from Python.

**Step 1.1 — Create docker-compose.yml**

Start with just postgres and redis (comment out proxy, dashboard, prometheus for now):
```bash
docker-compose up -d postgres redis
docker-compose ps   # Both should be healthy within 15 seconds
```

**Step 1.2 — Create migration files** from Section 7:
```bash
mkdir migrations
# Create 001_requests.sql, 002_cache.sql, 003_analytics.sql
```

Apply migrations (Postgres runs them automatically from the volume mount):
```bash
docker-compose down postgres
docker-compose up -d postgres
sleep 10

# Verify tables created
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c "\dt"
# Should show: requests, semantic_cache, daily_analytics (view)
```

**Step 1.3 — Create proxy/ directory and requirements:**
```bash
mkdir -p proxy/routers proxy/providers
touch proxy/__init__.py proxy/routers/__init__.py proxy/providers/__init__.py
pip install -r proxy/requirements.txt
```

**Step 1.4 — Create proxy/model_registry.py** from Section 4.1. This is the most important file — take time to understand every field.

**Step 1.5 — Test the registry:**
```python
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
```

**Day 1 Checkpoint:** Database up with schema. Model registry complete with 15+ models across 6 providers. Can query and calculate costs from Python.

---

### Day 2 — Classifier + Router

**Goal:** classify_complexity() works correctly on diverse prompts. select_model() returns the right model for each complexity level.

**Step 2.1 — Create proxy/settings.py** from Section 9.1.

**Step 2.2 — Create proxy/classifier.py** from Section 5.2.

**Step 2.3 — Test the classifier on diverse prompts:**
```python
# test_classifier.py
from proxy.classifier import classify_complexity

test_cases = [
    # Expected cheap
    ([{"role": "user", "content": "What is 2+2?"}], "cheap"),
    ([{"role": "user", "content": "What is the capital of France?"}], "cheap"),
    ([{"role": "user", "content": "Translate 'hello' to Spanish"}], "cheap"),
    ([{"role": "user", "content": "Define recursion"}], "cheap"),

    # Expected mid
    ([{"role": "user", "content": "Summarize the key points of machine learning in 3 paragraphs"}], "mid"),
    ([{"role": "user", "content": "Write a Python function to merge two sorted lists"}], "mid"),
    ([{"role": "user", "content": "Compare React and Vue.js for a large-scale application"}], "mid"),

    # Expected frontier
    ([{"role": "user", "content": "Analyze the macroeconomic implications of quantitative easing on emerging market debt"}], "frontier"),
    ([{"role": "user", "content": "Review and critique this code, explain step by step what's wrong and how to optimize it: " + "def fib(n):\n  if n<=1: return n\n  return fib(n-1)+fib(n-2)"}], "frontier"),
    ([{"role": "user", "content": "Write a persuasive essay arguing for and against universal basic income, synthesizing economic research"}], "frontier"),
]

print("Classifier Test Results:")
print("=" * 80)
correct = 0
for messages, expected in test_cases:
    result = classify_complexity(messages)
    status = "✓" if result["tier"] == expected else "✗"
    if result["tier"] == expected:
        correct += 1
    print(f"{status} Score: {result['score']:.2f} | Tier: {result['tier']:8s} | Expected: {expected:8s}")
    print(f"  Prompt: {messages[0]['content'][:60]!r}...")
    print(f"  Signals: {result['signals'][:3]}")
    print()

print(f"Accuracy: {correct}/{len(test_cases)} = {correct/len(test_cases)*100:.0f}%")
```

The classifier won't be perfect — that's fine. 75-85% accuracy on this test set is good. If a tier is consistently wrong, adjust the keyword weights in `COMPLEX_SIGNALS` and `SIMPLE_SIGNALS`.

**Step 2.4 — Create proxy/router.py** from Section 5.3.

**Step 2.5 — Test the router:**
```python
# test_router.py
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
```

**Day 2 Checkpoint:** Classifier routes prompts to the right tier. Router selects correct model with failover chain. Both work correctly for auto, cheapest, best, and specific model aliases.

---

### Day 3 — Provider Adapters + First Real LLM Call

**Goal:** Make a real LLM call through your proxy. The full path: classify → select → format → call provider → parse → return.

**Prerequisites:** Have at least one API key configured. Start with whichever you have (Anthropic or OpenAI). Search: "httpx async python tutorial", "Anthropic API quickstart Python".

**Step 3.1 — Create proxy/providers/base.py** from Section 9.2.

**Step 3.2 — Create provider adapters** from Section 9.2. Start with the provider whose key you have. Build Anthropic first if you have that key (the format translation is the most interesting to understand).

**Step 3.3 — Test each provider directly:**
```python
# test_anthropic.py
import asyncio
from proxy.providers.anthropic_provider import AnthropicProvider

async def test():
    provider = AnthropicProvider()
    response = await provider.complete(
        model="claude-haiku-4-5",  # Use cheapest for testing
        messages=[
            {"role": "user", "content": "Say exactly: 'Hello from Anthropic'"}
        ],
        max_tokens=50,
        temperature=0.0
    )
    print(f"Content: {response.content}")
    print(f"Tokens: {response.prompt_tokens}p + {response.completion_tokens}c")
    print(f"Model: {response.model}")
    print(f"Finish: {response.finish_reason}")

asyncio.run(test())
```

Expected output:
```
Content: Hello from Anthropic
Tokens: 24p + 6c
Model: claude-haiku-4-5-20251001
Finish: stop
```

**Step 3.4 — Create proxy/providers/__init__.py** with `get_provider()` from Section 9.2.

**Step 3.5 — Create proxy/db.py:**
```python
import asyncpg
from proxy.settings import settings

async def create_pool():
    return await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20
    )

async def get_db(request):
    return request.app.state.db_pool
```

**Step 3.6 — Create proxy/cost.py** from Section 9.5.

**Step 3.7 — Create proxy/main.py** from Section 13.

**Step 3.8 — Create proxy/routers/completions.py** from Section 9.4. This is the largest file — take it step by step. The core flow is the 10-step sequence at the top of the handler.

**Step 3.9 — Start the proxy and make your first proxied call:**
```bash
source .venv/bin/activate
cd proxy
uvicorn main:app --reload --port 8000
```

```bash
# Test with curl — this should route through your proxy and call a real LLM
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'
```

Expected response includes:
```json
{
  "choices": [{"message": {"content": "4"}, "finish_reason": "stop"}],
  "x_neuralgate": {
    "complexity_tier": "cheap",
    "selected_model": "claude-haiku-4-5",
    "total_cost_usd": 0.0000048,
    "total_latency_ms": 387
  }
}
```

**Step 3.10 — Test with more prompts:**
```bash
# Should route to frontier tier
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Analyze step by step the time and space complexity of quicksort and compare it with merge sort, explaining the tradeoffs in different scenarios"}]
  }'

# Force cheapest model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "cheapest", "messages": [{"role": "user", "content": "Explain recursion"}]}'

# Force specific model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet-4-5", "messages": [{"role": "user", "content": "Hello"}]}'
```

Verify in the `x_neuralgate` field that:
- Simple prompts route to cheap tier
- Complex prompts route to frontier tier
- `model: cheapest` always goes to cheap tier
- Specific model names bypass the classifier

**Step 3.11 — Verify logs in Postgres:**
```bash
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c \
  "SELECT selected_model, complexity_tier, complexity_score, total_cost_usd, total_latency_ms
   FROM requests ORDER BY created_at DESC LIMIT 5"
```

**Day 3 Checkpoint:** Real LLM calls through the proxy. Classification working. Routing working. Logs persisting to Postgres. This is the core system — everything else builds on this.

---

### Day 4 — Second Provider + Failover + Multiple Providers

**Goal:** At least 2 providers working. Failover tested. `GET /v1/models` working.

**Step 4.1 — Add your second provider** (OpenAI if you started with Anthropic, or vice versa). Add the key to `.env`, create the provider class, add to `get_provider()`.

**Step 4.2 — Test cross-provider routing:**
```bash
# Use preferred provider header
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Preferred-Provider: openai" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "What is 2+2?"}]}'
# x_neuralgate.selected_provider should be "openai"
```

**Step 4.3 — Test failover manually:**

Temporarily add a bad API key for a provider, then send a request that would route there. Verify it falls back to the next provider in the chain.

**Step 4.4 — Add DeepSeek** (cheapest to test with). Since it's OpenAI-compatible, copy `openai_provider.py`, change `BASE_URL = "https://api.deepseek.com/v1"` and the key field. Takes 10 minutes.

**Step 4.5 — Create proxy/routers/models.py:**
```python
from fastapi import APIRouter
from proxy.model_registry import MODEL_REGISTRY
from proxy.settings import get_available_providers

router = APIRouter()

@router.get("/v1/models")
async def list_models():
    available_providers = get_available_providers()
    models = [
        {
            "id": "auto",
            "object": "model",
            "description": "Automatically route to optimal model based on complexity"
        },
        {
            "id": "cheapest",
            "object": "model",
            "description": "Always use cheapest available model"
        },
        {
            "id": "balanced",
            "object": "model",
            "description": "Always use mid-tier model"
        },
        {
            "id": "best",
            "object": "model",
            "description": "Always use frontier model"
        }
    ]

    for model_id, info in MODEL_REGISTRY.items():
        if info["provider"] in available_providers:
            models.append({
                "id": model_id,
                "object": "model",
                **info
            })

    return {"object": "list", "data": models}
```

**Step 4.6 — Test with OpenAI Python SDK (the real integration test):**
```python
# test_sdk.py
# This proves your proxy is truly OpenAI-compatible
from openai import OpenAI

client = OpenAI(
    api_key="any-string-works",  # Your proxy doesn't auth yet
    base_url="http://localhost:8000/v1"
)

# Should just work — same code as talking to OpenAI directly
response = client.chat.completions.create(
    model="auto",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of Japan?"}
    ]
)
print(response.choices[0].message.content)
print(response.model)  # The actual model that ran
```

**Day 4 Checkpoint:** Multiple providers working. Failover tested. OpenAI SDK works against your proxy without modification.

---

### Day 5 — Semantic Cache

**Goal:** Identical prompts return cached responses instantly. Similar prompts hit the semantic cache. Cache stats visible in Postgres.

**Prerequisites:** Read Section 3.5 (semantic caching) again. You need OpenAI API key for embeddings (or use a local embedding model — see note in `cache.py`). Search: "pgvector python cosine similarity search", "Redis setex python async".

**Step 5.1 — Verify pgvector extension:**
```bash
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c "SELECT '[1,2,3]'::vector;"
```

**Step 5.2 — Create proxy/cache.py** from Section 10.1.

**Step 5.3 — Wire cache into completions.py** — the cache check and store calls are already in the handler from Section 9.4. Verify both calls are in place.

**Step 5.4 — Test exact cache:**
```bash
# Send same request twice
MSG='{"model": "auto", "messages": [{"role": "user", "content": "What is the speed of light?"}]}'

# First call — should hit LLM
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "$MSG"
# x_neuralgate.cache_hit should be false, latency ~400ms

sleep 2

# Second call — should hit exact cache
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "$MSG"
# x_neuralgate.cache_hit should be true, latency <10ms!!!
```

**Step 5.5 — Test semantic cache:**
```bash
# First prompt
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "What is the capital of France?"}]}'

sleep 3  # Wait for cache to store

# Semantically similar but different wording
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "Which city is the capital of France?"}]}'
# cache_hit should be true, cache_similarity ~0.97
```

**Step 5.6 — Check cache stats in Postgres:**
```bash
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c \
  "SELECT prompt_text, hit_count, total_cost_saved_usd FROM semantic_cache ORDER BY hit_count DESC LIMIT 5"
```

**Step 5.7 — Test cache bypass:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Skip-Cache: true" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "What is the capital of France?"}]}'
# Should NOT hit cache — always calls LLM fresh
```

**Day 5 Checkpoint:** Two-level semantic cache working. Exact hits return in <10ms. Semantic hits working with configurable threshold. Cache bypass working.

---

### Day 6 — Analytics API + React Dashboard

**Goal:** All analytics endpoints return correct data. React dashboard shows live charts.

**Step 6.1 — Create proxy/routers/analytics.py:**
```python
from fastapi import APIRouter, Query
from typing import Optional
import asyncpg

router = APIRouter()

@router.get("/summary")
async def get_summary(request, days: int = Query(default=7, ge=1, le=90)):
    async with request.app.state.db_pool.acquire() as conn:
        # Basic stats
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) AS total_requests,
                SUM(total_cost_usd) AS total_cost,
                SUM(cost_savings_usd) AS total_savings,
                AVG(total_latency_ms) AS avg_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*) AS cache_hit_rate,
                SUM(CASE WHEN cache_hit THEN total_tokens ELSE 0 END) AS tokens_saved_by_cache,
                SUM(CASE WHEN cache_hit THEN frontier_cost_usd ELSE 0 END) AS cost_saved_by_cache
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

        # By tier
        tier_rows = await conn.fetch("""
            SELECT complexity_tier, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
              AND complexity_tier IS NOT NULL
            GROUP BY complexity_tier
        """, str(days))

        # By provider
        provider_rows = await conn.fetch("""
            SELECT selected_provider, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY selected_provider
            ORDER BY cost DESC
        """, str(days))

        # By model
        model_rows = await conn.fetch("""
            SELECT selected_model, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY selected_model
            ORDER BY cost DESC
            LIMIT 10
        """, str(days))

    total_cost = float(stats["total_cost"] or 0)
    total_savings = float(stats["total_savings"] or 0)
    baseline = total_cost + total_savings

    return {
        "period_days": days,
        "total_requests": stats["total_requests"],
        "total_cost_usd": round(total_cost, 4),
        "total_savings_usd": round(total_savings, 4),
        "savings_percent": round(total_savings / baseline * 100, 1) if baseline > 0 else 0,
        "cache_hit_rate": round(float(stats["cache_hit_rate"] or 0), 3),
        "tokens_saved_by_cache": int(stats["tokens_saved_by_cache"] or 0),
        "avg_latency_ms": round(float(stats["avg_latency"] or 0)),
        "p95_latency_ms": round(float(stats["p95_latency"] or 0)),
        "by_tier": {
            row["complexity_tier"]: {
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 4)
            }
            for row in tier_rows
        },
        "by_provider": {
            row["selected_provider"]: {
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 4)
            }
            for row in provider_rows
        },
        "by_model": [
            {
                "model": row["selected_model"],
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 4)
            }
            for row in model_rows
        ]
    }

# Add /routing, /savings, /cache endpoints following the same pattern
# Each queries the requests table differently and returns structured data
```

**Step 6.2 — Test analytics endpoints:**
```bash
# Generate some traffic first (send 20+ requests to have meaningful data)
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"auto\", \"messages\": [{\"role\": \"user\", \"content\": \"Question $i: what is $i + $i?\"}]}" > /dev/null
done

curl http://localhost:8000/analytics/summary | python3 -m json.tool
```

**Step 6.3 — Set up React dashboard:**
```bash
cd dashboard
npm create vite@latest . -- --template react
npm install recharts
```

**Step 6.4 — Create vite.config.js:**
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

**Step 6.5 — Build SavingsChart.jsx** (most impressive component):
```jsx
import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export function SavingsChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch('/api/analytics/savings?days=7')
      .then(r => r.json())
      .then(d => setData(d.daily_savings || []));
  }, []);

  return (
    <div style={{ padding: 24, background: '#fff', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h3 style={{ margin: '0 0 4px' }}>Cost: Actual vs All-Frontier</h3>
      <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: 13 }}>
        Green area = money saved by intelligent routing
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={v => `$${v.toFixed(3)}`} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v, n) => [`$${v.toFixed(4)}`, n]} />
          <Legend />
          <Line type="monotone" dataKey="hypothetical" stroke="#ef4444"
                strokeDasharray="5 5" name="If all-frontier" dot={false} />
          <Line type="monotone" dataKey="actual" stroke="#22c55e"
                strokeWidth={2} name="Actual cost" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Step 6.6 — Build the routing pie chart, live request feed, and cost cards.** Follow the same pattern as SavingsChart but query different endpoints.

**Day 6 Checkpoint:** All analytics endpoints returning real data. Dashboard shows routing distribution, cost comparison, and live request feed. The savings chart is the key one — shows concrete dollar value.

---

### Day 7 — Docker + Load Test + Benchmarks

**Goal:** Everything runs with `docker-compose up`. Benchmark numbers measured. README written.

**Step 7.1 — Create Dockerfiles** from Section 13.

**Step 7.2 — Full Docker Compose up:**
```bash
docker-compose down -v  # Clean slate
docker-compose up --build
curl http://localhost:8000/health
```

**Step 7.3 — Create load-test/benchmark.py:**
```python
import asyncio
import httpx
import time
import statistics
import json

BASE = "http://localhost:8000"

# Diverse prompt set — tests classifier routing
TEST_PROMPTS = [
    # Cheap tier expected
    ("What is 2+2?", "cheap"),
    ("Define photosynthesis", "cheap"),
    ("What year was the Eiffel Tower built?", "cheap"),
    ("Translate 'hello' to French", "cheap"),
    ("What is the capital of Japan?", "cheap"),

    # Mid tier expected
    ("Write a Python function to find the nth Fibonacci number", "mid"),
    ("Summarize the key differences between REST and GraphQL", "mid"),
    ("Explain how TCP/IP works in 3 paragraphs", "mid"),

    # Frontier tier expected
    ("Analyze step by step the tradeoffs between different database indexing strategies for read-heavy vs write-heavy workloads", "frontier"),
    ("Critique and improve this algorithm, explain your reasoning: " + "def sort(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)-1):\n            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]\n    return arr", "frontier"),
]

async def one_request(client, prompt, expected_tier):
    t0 = time.monotonic()
    r = await client.post("/v1/chat/completions", json={
        "model": "auto",
        "messages": [{"role": "user", "content": prompt}]
    }, timeout=60.0)
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    data = r.json()
    ng = data.get("x_neuralgate", {})
    return {
        "latency_ms": elapsed_ms,
        "model": ng.get("selected_model"),
        "tier": ng.get("complexity_tier"),
        "expected_tier": expected_tier,
        "correct_tier": ng.get("complexity_tier") == expected_tier,
        "cost_usd": ng.get("total_cost_usd", 0),
        "cache_hit": ng.get("cache_hit", False),
    }

async def run_benchmark(n_repeats=3):
    print(f"Benchmarking NeuralGate — {n_repeats} passes × {len(TEST_PROMPTS)} prompts\n")

    all_results = []

    async with httpx.AsyncClient(base_url=BASE) as client:
        for _ in range(n_repeats):
            tasks = [one_request(client, p, t) for p, t in TEST_PROMPTS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend([r for r in results if isinstance(r, dict)])

    latencies = [r["latency_ms"] for r in all_results if not r["cache_hit"]]
    cache_hits = [r for r in all_results if r["cache_hit"]]
    tier_correct = [r for r in all_results if r["correct_tier"]]
    total_cost = sum(r["cost_usd"] for r in all_results)

    sorted_l = sorted(latencies)

    print(f"Total requests: {len(all_results)}")
    print(f"Cache hit rate: {len(cache_hits)/len(all_results)*100:.0f}%")
    print(f"Tier accuracy: {len(tier_correct)/len(all_results)*100:.0f}%")
    print(f"\nLatency (non-cached):")
    print(f"  P50: {sorted_l[len(sorted_l)//2]}ms")
    print(f"  P95: {sorted_l[int(len(sorted_l)*0.95)]}ms")
    print(f"  Max: {max(sorted_l)}ms")
    print(f"\nCost: ${total_cost:.6f} for {len(all_results)} requests")
    print(f"Avg cost per request: ${total_cost/len(all_results):.8f}")

    # Model distribution
    from collections import Counter
    model_dist = Counter(r["model"] for r in all_results if not r["cache_hit"])
    print(f"\nModel distribution (non-cached):")
    for model, count in model_dist.most_common():
        pct = count / len(all_results) * 100
        print(f"  {model}: {count} ({pct:.0f}%)")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

**Step 7.4 — Run benchmarks:**
```bash
python load-test/benchmark.py
```

**Record your actual numbers** — you'll put these in your README and talk about them in interviews.

**Step 7.5 — Write README.md** with:
- What it is (one paragraph)
- Architecture diagram (ASCII)
- How to run (`cp .env.example .env && docker-compose up`)
- Benchmark results table
- Supported models table
- API examples with curl
- Design tradeoffs section

---

### Day 7.5 — Auth, Rate Limiting, and Replay

> This is an optional eighth day if you have time. These three features make the project feel production-grade and give you two more strong talking points in interviews.

**Goal:** Proxy requires an API key. Rate limiting enforced per client. Replay button working in dashboard.

**Step 7.5.1 — Run migration 004:**
```bash
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -f /docker-entrypoint-initdb.d/004_security.sql
# Verify tables created
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c "\dt"
# Should now show: requests, semantic_cache, daily_analytics, request_payloads, rate_limit_config
```

**Step 7.5.2 — Generate a proxy API key:**
```bash
python3 -c "import secrets; print('ng-' + secrets.token_hex(32))"
# Copy the output into your .env as PROXY_API_KEY=ng-...
```

**Step 7.5.3 — Create `proxy/middleware/` directory and implement auth:**
```bash
mkdir proxy/middleware
touch proxy/middleware/__init__.py
```
Create `proxy/middleware/auth.py` from Section 9.6.

**Step 7.5.4 — Test auth is working:**
```bash
# Without key — should get 401
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# With key — should get model list
curl -s -H "Authorization: Bearer ng-your-key" \
  http://localhost:8000/v1/models | python3 -m json.tool

# Health should still work without key
curl http://localhost:8000/health
```

**Step 7.5.5 — Implement rate limiting:**
Create `proxy/middleware/rate_limit.py` from Section 9.7. Register both middleware in `main.py` — order matters (auth first, then rate limit).

**Step 7.5.6 — Test rate limiting:**
```bash
# Send 65 rapid requests — should see 429 after the 60th
for i in {1..65}; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/v1/chat/completions \
    -H "Authorization: Bearer ng-your-key" \
    -H "X-Client-ID: test-blast" \
    -H "Content-Type: application/json" \
    -d '{"model":"cheapest","messages":[{"role":"user","content":"hi"}]}')
  echo "Request $i: HTTP $CODE"
done
```

You should see HTTP 200 for requests 1-60 and HTTP 429 for 61-65. The response body will include `retry_after` and the current window counts.

**Step 7.5.7 — Enable payload storage and implement replay:**
Add `STORE_PAYLOADS=true` to `.env`. Add the `_store_payload` background task to `completions.py` (Section 9.8). Create `proxy/routers/replay.py` from Section 9.8. Register it in `main.py`.

**Step 7.5.8 — Test replay:**
```bash
# Send a request
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ng-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is recursion?"}]}')

# Extract request_id from response
REQUEST_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['x_neuralgate']['request_id'])")

# Replay it
curl -s -X POST http://localhost:8000/requests/$REQUEST_ID/replay \
  -H "Authorization: Bearer ng-your-key" | python3 -m json.tool
```

You should see the `diff` block showing original vs replayed model, cost, and latency.

**Step 7.5.9 — Add Replay button to dashboard:**
Add the replay button and modal to `LiveRequestFeed.jsx` from Section 9.8.

**Day 7.5 Checkpoint:** Unauthenticated requests return 401. Rate-limited clients get 429 with Retry-After header. Replay endpoint returns diff of original vs re-run. Dashboard shows replay button on each request row.

### What Numbers to Report

**Routing accuracy:** What % of requests were routed to the correct tier? Your heuristic classifier won't be perfect — 75-85% is realistic and honest. Report it.

**Cost savings:** The headline metric. Run 100 requests through your proxy. Compare actual cost vs if everything went to the frontier model. The savings number is usually impressive — 60-80% cheaper with intelligent routing.

**Cache hit rate:** After sending the same 20 prompts 5 times each, the cache hit rate should approach 80%+ (first pass misses, subsequent passes hit). Report hit rate and latency improvement.

**Latency:**
- Non-cached P50: ~400-900ms (depends on provider and model)
- Non-cached P95: ~1500-3000ms
- Cached P50: ~5-15ms (Redis hit + pgvector search)
- This is a compelling story: 100x latency improvement for cache hits

### Sample README Results Table

```markdown
## Benchmark Results (100 test prompts, 3 providers)

| Metric | Value |
|--------|-------|
| Routing accuracy | 81% |
| Actual cost | $0.0034 |
| Cost if all-frontier | $0.0287 |
| **Savings** | **88%** |
| Cache hit rate (warm) | 34% |
| P50 latency (non-cached) | 487ms |
| P95 latency (non-cached) | 1,840ms |
| P50 latency (cached) | 8ms |
```

---

## 16. Design Tradeoffs

**Include this in your README.**

**Heuristic classifier over ML classifier**

A trained ML classifier (fine-tuned DistilBERT, for example) would have higher accuracy than the heuristic approach. The tradeoff: training data, training time, model hosting overhead, and a cold start problem — you'd need thousands of labeled prompt-response pairs with quality judgments before the classifier is useful. The heuristic approach is live immediately, transparent (you can read the signal weights and understand decisions), and sufficient for routing decisions where occasional misclassification has low cost. For v2, a lightweight trained classifier would be a natural improvement once you have real usage data to train on.

**Two-level cache (exact + semantic) over single cache**

Exact-match cache has zero false positive rate but misses semantic equivalents. Semantic-only cache requires an embedding call for every request, adding ~100ms latency. The two-level approach: exact match checks Redis in <1ms (no embedding needed), semantic match only triggers on an exact miss. In practice, exact hits dominate for repeated queries (cron jobs, health checks, repeated user interactions), while semantic hits catch paraphrased queries.

**Stateless proxy over stateful session tracking**

The proxy doesn't maintain conversation sessions. Every request is independent. This simplifies horizontal scaling dramatically — any instance can handle any request. The tradeoff: you can't do session-level cost attribution or per-user rate limiting without a session layer. For v1, stateless is the right call.

**OpenAI-format compatibility over native provider formats**

Translating every provider to OpenAI format means clients never need to change their code. The cost: adapter logic for each new provider, and some provider-specific features (Anthropic's extended thinking, Google's grounding) can't be exposed through the generic format without custom headers. For a proxy focused on cost optimization, the portability benefit outweighs the feature limitations.

**Synchronous response over streaming**

Streaming (returning tokens as they're generated) is the default for most LLM UIs. Not implementing it simplifies the proxy significantly — streaming requires server-sent events, proxy buffering logic, and streaming responses from pgvector and Redis that are more complex. V1 is non-streaming; streaming support is the obvious v2 extension.

**Static bearer token over full user authentication**

The proxy uses a single shared API key rather than per-user accounts, JWTs, or a sign-up flow. This is the right call for a developer-facing infrastructure tool — the consumer is an application, not an end user. Full user auth would double the build time and shift the product narrative from "LLM infrastructure" to "consumer SaaS." The `X-Client-ID` header provides the attribution and rate limiting granularity needed without a user database.

**Redis sliding window over fixed window for rate limiting**

A fixed window rate limiter resets at the top of every minute, enabling burst attacks at window boundaries (send 60 requests at 12:00:59, 60 more at 12:01:01 — 120 requests in 2 seconds). A sliding window counts requests in the last N seconds from the current moment, smoothing bursts. The tradeoff: sliding window requires a Redis sorted set with one entry per request (more memory), versus a simple counter for fixed window. For request volumes a portfolio proxy handles, the memory cost is negligible — sliding window is the correct choice.

**Opt-in payload storage for replay**

Storing raw message content for every request has privacy implications — you're logging what users ask. Making it opt-in via `STORE_PAYLOADS=true` means the default is privacy-preserving (only metadata is stored), and operators explicitly choose to enable replay. This is the same pattern used by most API observability tools.

---

## 17. Interview Preparation

### 60-Second Project Explanation

"I built NeuralGate, an LLM cost-optimization proxy that sits between applications and every major LLM provider — Anthropic, OpenAI, Google, DeepSeek, xAI, Mistral. It's OpenAI-compatible, so existing apps point their base_url at my proxy and immediately get intelligent routing without any code changes.

The core is a prompt complexity classifier that analyzes each request using heuristic signals — prompt length, keywords, code presence, conversation depth — and routes it to the cheapest model that can handle it. Simple questions go to Claude Haiku or GPT-4o-mini. Complex analysis goes to Claude Opus or GPT-4o. On a benchmark of 100 diverse prompts, routing cost 88% less than sending everything to the frontier model with 81% routing accuracy.

It also has two-level semantic caching: exact-match via Redis SHA-256 hashing, and approximate semantic matching via pgvector cosine similarity on OpenAI embeddings. Cache hits return in under 10ms vs 400-900ms for live LLM calls. There's a full analytics layer tracking cost, savings, cache performance, and routing decisions, with a React dashboard showing the savings in real time."

---

### Technical Questions and Strong Answers

**Q: How does your classifier decide which tier to use?**

A: "It's a heuristic scoring system starting at 0.40 — neutral mid-point. Then I apply weighted signals: prompt length adds or subtracts based on token count (very short prompts are usually simple questions), keywords like 'analyze' and 'step by step' push the score up, keywords like 'define' and 'translate' push it down, code presence adds 0.15, and long multi-turn conversations add 0.10 for the context complexity. The final score maps to cheap (below 0.35), mid (0.35-0.65), or frontier (above 0.65). On my benchmark set I get 81% accuracy. The misclassifications mostly happen at tier boundaries — a medium-complexity prompt scored 0.64 going to mid instead of frontier is low-cost because the mid-tier model usually handles it fine. The high-cost mistake would be routing something genuinely complex to cheap tier, and that happens about 5% of the time in my testing."

**Q: How does the semantic cache work? Why not just exact-match?**

A: "Exact-match cache hashes the messages array with SHA-256 and checks Redis. It's O(1) and has zero false positive rate, but it misses semantically equivalent prompts — 'What is the capital of France?' and 'Which city is France's capital?' are different strings but identical in intent. The semantic layer embeds the prompt using text-embedding-3-small (1536 dimensions), then searches pgvector for any cached embedding within cosine distance 0.05 (similarity > 0.95). If a hit exists, the cached response is returned without calling any LLM. The two-level design matters: I only run the embedding call on exact-cache misses. Exact hits account for most repeated queries in production — health checks, cron jobs, users re-submitting the same question — and they're served in under 1ms from Redis without any embedding overhead."

**Q: How do you handle provider failover?**

A: "Each model has a failover chain in the registry — an ordered list of equivalent models from different providers. When a request fails with a 5xx or 429, the handler catches the exception and tries the next model in the chain. Client errors (4xx for bad requests) don't trigger failover — they propagate directly. I log `failover_occurred=true` and `original_model` when this happens so I can track which providers are unreliable. In the analytics, the failover rate surfaces as a metric. If it spikes for a specific provider, that's a signal to deprioritize that provider or adjust the model registry."

**Q: What's the difference between how you talk to Anthropic vs OpenAI?**

A: "Both take the same internal ProviderResponse output, but the request formats are completely different. OpenAI uses a flat messages array with system/user/assistant roles. Anthropic separates the system prompt into a top-level 'system' field and doesn't accept a 'system' role in the messages array. Google Gemini uses a 'contents' array with 'parts' sub-arrays and calls assistant messages 'model' instead of 'assistant'. DeepSeek, xAI, and Mistral all use OpenAI-compatible formats — they were designed for drop-in compatibility. My BaseProvider abstract class defines a `format_request()` and `parse_response()` interface. Each provider subclass implements the translation logic. Adding a new provider is: implement BaseProvider, register in the factory, add API key to settings."

**Q: What's the cost of running the proxy itself on each request?**

A: "Three operations: a Redis exact-cache check (~0.5ms), a tiktoken token count (~0.2ms, pure Python), and on cache misses an embedding call for semantic cache (~100ms). The embedding call is the expensive one. At $0.02/million tokens and ~50 tokens per prompt, each embedding costs $0.000001 — negligible. For 1 million requests per day, the embedding overhead is $1/day. Versus the LLM savings, it's a rounding error. The Postgres log write is async — it never blocks the response. Total proxy overhead excluding the embedding: ~2-3ms."

**Q: How would you improve the classifier?**

A: "The heuristic approach has a ceiling — it doesn't understand semantic complexity, only surface signals. A natural v2 would train a lightweight binary classifier on labeled data: pairs of (prompt, routing_decision) where the routing decision is validated by comparing output quality between cheap and frontier models on the same prompt. With a few thousand labeled examples you could fine-tune DistilBERT or use a simple logistic regression on embeddings. The challenge is the label generation — you need human or LLM-as-judge evaluation of whether the cheap model's response was adequate. Once you have real usage data flowing through the proxy, you can bootstrap this: flag cases where the cheap model response is short or truncated (proxy for failure) and use those as negative training examples."

**Q: How does the rate limiter work and why Redis?**

A: "It's a sliding window counter implemented with a Redis sorted set. For each client, every request adds an entry with score equal to the current Unix timestamp. Before processing a request, I remove all entries older than the window (60 seconds for the per-minute limit) and count what remains. If count exceeds the limit, return 429. Redis because rate limit checks happen on every single request before any processing — they need to be sub-millisecond. A Postgres query is 2-5ms; a Redis sorted set operation is under 0.5ms. I also use a pipeline to batch the four Redis operations (remove stale, count, add, expire) into a single round trip."

**Q: Why sliding window over fixed window rate limiting?**

A: "Fixed window has a boundary burst problem: a client can send 60 requests at 12:00:59 and 60 more at 12:01:01 — 120 requests in 2 seconds while technically staying under '60 per minute.' Sliding window measures the last 60 seconds from the current moment, so that burst would get caught. The tradeoff is memory: sliding window stores one sorted set entry per request versus a single counter for fixed window. At the volumes a proxy like this handles, that's negligible — a few thousand entries per active client."

**Q: How does request replay work? Why is it useful?**

A: "Replay re-runs a logged request through the full proxy pipeline using the stored message payload and returns a comparison of the original vs the new result — model selected, cost, latency, and the actual response content. It's useful for two things: first, debugging routing decisions after you tune the classifier weights (did that prompt that went to Haiku now correctly route to Sonnet?); second, verifying failover recovery (a request that failed due to a provider outage can be replayed once the provider is back). The payload storage is opt-in via an environment variable because storing raw messages has privacy implications — you're logging user content. Default is off."

**Q: How does the proxy API key work? Why not JWT?**

A: "It's a static bearer token checked in a FastAPI middleware that runs before every handler. If the Authorization header is missing or wrong, the request is rejected with 401 before anything else runs — zero cost incurred. JWT would be overkill for a developer-facing infrastructure tool. JWTs add token expiry, refresh flows, signing key management — none of which matter when the consumer is an application configured once by a developer, not an end user logging in from a browser. The single shared secret pattern is the same thing the OpenAI API itself uses at the most basic level."

---

## 18. Resume Bullets

Fill in benchmark numbers from your actual Day 7 results.

---

**NeuralGate | Python, FastAPI, PostgreSQL, Redis, pgvector, Docker**

- Built an OpenAI-compatible LLM proxy routing requests across 15+ models from 6 providers (Anthropic, OpenAI, Google, DeepSeek, xAI, Mistral) using a heuristic complexity classifier, reducing inference cost by [X]% vs always routing to frontier models on a [N]-prompt benchmark.
- Implemented two-level semantic caching — SHA-256 exact-match via Redis and cosine similarity search via pgvector on OpenAI embeddings — reducing cache-hit latency from ~[X]ms to under 10ms and eliminating redundant LLM calls for semantically equivalent prompts.
- Engineered per-client rate limiting via a Redis sliding window sorted set, enforcing configurable request quotas (per-minute, per-hour, per-day) across clients with sub-millisecond overhead per check and automatic 429 responses with Retry-After headers.
- Built a request replay system storing message payloads in PostgreSQL and re-running historical requests through the live routing pipeline, returning a structured diff of original vs replayed model selection, cost, and latency — used for validating classifier tuning without live traffic.
- Secured the proxy with bearer token authentication enforced in FastAPI middleware, rejecting unauthenticated requests before routing with zero LLM cost incurred, with provider adapter layer translating between OpenAI, Anthropic, and Google Gemini formats and automatic failover across providers on 5xx and rate-limit errors.
- Tracked per-request cost, routing decisions, and complexity signals in PostgreSQL with a React analytics dashboard showing real-time cost savings, cache performance, routing distribution, and a live request feed with one-click replay.

---

### Signal Breakdown

| Phrase | Signal |
|---|---|
| "OpenAI-compatible" | You understand API standards and built to them |
| "15+ models from 6 providers" | Breadth — you built real multi-provider infrastructure |
| "heuristic complexity classifier" | Honest about approach, can explain tradeoffs |
| "[X]% cost reduction" | Concrete measurable outcome — you benchmark your work |
| "two-level semantic caching" | Architectural depth — not just "I added Redis caching" |
| "SHA-256 exact-match via Redis" | Specific mechanism |
| "cosine similarity search via pgvector" | Vector search infrastructure knowledge |
| "provider adapter layer" | You understand that different APIs need translation |
| "automatic failover" | Reliability engineering thinking |
| "drop-in compatible with any OpenAI SDK client" | Practical systems thinking |

---

## Appendix: Quick Reference

### Start the system
```bash
cp .env.example .env
# Add your API keys

docker-compose up --build
curl http://localhost:8000/health
open http://localhost:3000   # Dashboard
```

### Make your first routed request
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Your question here"}]
  }'
```

### Use with OpenAI SDK (no code changes needed)
```python
from openai import OpenAI
client = OpenAI(api_key="any-key", base_url="http://localhost:8000/v1")
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Check routing analytics
```bash
curl http://localhost:8000/analytics/summary?days=7 | python3 -m json.tool
```

### Test semantic cache
```bash
# Send same prompt twice — second should return cache_hit=true
PROMPT='{"model":"auto","messages":[{"role":"user","content":"What is machine learning?"}]}'
curl -X POST http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d "$PROMPT"
sleep 2
curl -X POST http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d "$PROMPT"
```

### Useful Postgres queries
```sql
-- Cost by model today
SELECT selected_model, COUNT(*), ROUND(SUM(total_cost_usd)::numeric, 6) AS cost
FROM requests WHERE created_at > now() - interval '24 hours'
GROUP BY selected_model ORDER BY cost DESC;

-- Cache hit rate today
SELECT
  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*) AS hit_rate,
  COUNT(*) AS total
FROM requests WHERE created_at > now() - interval '24 hours';

-- Routing distribution
SELECT complexity_tier, COUNT(*), ROUND(AVG(complexity_score)::numeric, 3) AS avg_score
FROM requests WHERE complexity_tier IS NOT NULL
GROUP BY complexity_tier ORDER BY complexity_tier;

-- Total savings
SELECT
  ROUND(SUM(total_cost_usd)::numeric, 4) AS actual,
  ROUND(SUM(frontier_cost_usd)::numeric, 4) AS if_all_frontier,
  ROUND(SUM(cost_savings_usd)::numeric, 4) AS saved
FROM requests WHERE created_at > now() - interval '7 days';
```

### Reset for a clean run
```bash
docker exec -it $(docker-compose ps -q postgres) \
  psql -U postgres -d neuralgate -c "TRUNCATE requests, semantic_cache;"
docker exec -it $(docker-compose ps -q redis) redis-cli FLUSHALL
```

---

*End of NeuralGate PRD v1.0*
