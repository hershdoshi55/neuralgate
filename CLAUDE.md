# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

NeuralGate is an OpenAI-compatible LLM reverse proxy that intelligently routes requests to the cheapest model capable of handling them. Clients point their OpenAI SDK at `http://localhost:8000/v1` and use `model="auto"` — the proxy classifies prompt complexity, selects the optimal model from a registry of 15+ models across 6 providers, handles failover, and logs cost/latency/routing decisions for analytics.

**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 (pgvector) · Redis 7 · Docker Compose · React (Vite)

## Development Setup

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Python env (from repo root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r proxy/requirements.txt

# Run the proxy (from repo root)
uvicorn proxy.main:app --host 0.0.0.0 --port 8000 --reload

# Run the dashboard (from dashboard/ directory)
cd dashboard
npm install && npm run dev
```

Database migrations are applied automatically when Postgres starts via the `./migrations:/docker-entrypoint-initdb.d` Docker volume mount. To re-apply migrations, `docker-compose down postgres && docker-compose up -d postgres`.

## Running Tests

All test scripts live in `tests/`. Always run them from the repo root:

```bash
# Classifier accuracy test
python tests/test_classifier.py

# Router selection test
python tests/test_router.py

# Direct provider tests
python tests/providers/test_anthropic.py   # or test_openai.py etc.

# SDK integration test (proxy must be running)
python tests/test_sdk.py

# Load test
python load-test/benchmark.py
```

**Rule: every new test file goes in `tests/` (or a subdirectory like `tests/providers/`, `tests/core/`). Never place test files in the repo root.**

## Architecture

### Request Flow

```
POST /v1/chat/completions
  1. Auth middleware (Bearer token)
  2. Rate limit middleware (Redis sliding window)
  3. Count tokens (tiktoken)
  4. Check semantic cache (exact: Redis SHA-256; semantic: pgvector cosine similarity)
     → Cache hit: return cached response, log async, cost=$0
  5. classify_complexity() → score 0.0–1.0 → tier (cheap/mid/frontier)
  6. select_model() → primary model + failover chain
  7. format_request() via provider adapter (OpenAI → provider-specific format)
  8. Call provider API with failover on 429/5xx
  9. parse_response() → normalized ProviderResponse
  10. store_semantic_cache() async
  11. log_request() to PostgreSQL async
  12. Return OpenAI-format response with x_neuralgate metadata
```

### Key Modules

- `proxy/model_registry.py` — All models with pricing, tier, context window. TIER_DEFAULTS and FAILOVER_CHAINS define routing hierarchy.
- `proxy/classifier.py` — Heuristic complexity scorer (0.0–1.0). Signals: prompt length, keyword weights, code presence, conversation length. Score < 0.35 → cheap, < 0.65 → mid, else frontier.
- `proxy/router.py` — `select_model()`: maps model alias (auto/cheapest/best/balanced/specific) to a model, filtering by context window and optional cost cap.
- `proxy/cache.py` — Two-level cache: L1 exact SHA-256 match in Redis, L2 semantic pgvector search using OpenAI `text-embedding-3-small` (1536 dims, threshold 0.95).
- `proxy/providers/` — `BaseProvider` ABC with `format_request()`, `parse_response()`, `complete()`. Anthropic and Google require format translation; DeepSeek/xAI/Mistral are OpenAI-compatible (copy `deepseek_provider.py`, change BASE_URL and API key).
- `proxy/middleware/auth.py` — Bearer token check; `PROXY_API_KEY` from `.env`.
- `proxy/middleware/rate_limit.py` — Redis sorted-set sliding window per client. Client ID from `X-Client-ID` header. Limits stored in `rate_limit_config` PostgreSQL table.

### Database Schema (PostgreSQL + pgvector)

- `requests` — Every proxy call: routing decision, tokens, cost, latency, complexity score, cache_hit. `total_tokens` and `total_cost_usd` are GENERATED columns.
- `semantic_cache` — Prompt embeddings (vector(1536)), response text, TTL. IVFFlat index for ANN search.
- `daily_analytics` — Materialized view aggregating requests by day/provider/model/tier. Refresh with `REFRESH MATERIALIZED VIEW CONCURRENTLY daily_analytics`.
- `request_payloads` — Raw message JSON for request replay (enabled with `STORE_PAYLOADS=true`).
- `rate_limit_config` — Per-client rate limit overrides.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | Main proxy endpoint (OpenAI-compatible) |
| GET | `/v1/models` | List available models |
| GET | `/analytics/summary` | Cost overview |
| GET | `/analytics/routing` | Routing decision breakdown |
| GET | `/analytics/savings` | Actual vs hypothetical frontier cost |
| GET | `/analytics/cache` | Cache hit rate and tokens saved |
| GET | `/analytics/recent` | Last N requests (used by LiveRequestFeed) |
| POST | `/requests/{id}/replay` | Re-run a logged request, compare results |
| GET/PUT | `/rate-limits/{client_id}` | View/update per-client rate limits |
| GET | `/health` | Provider connectivity + DB/Redis status |
| GET | `/metrics` | Prometheus metrics |

### Custom Request Headers

- `Authorization: Bearer <key>` — Required (PROXY_API_KEY)
- `X-Client-ID` — Tag requests for cost attribution and rate limiting
- `X-Preferred-Provider` — Prefer a specific provider (anthropic/openai/etc.)
- `X-Max-Cost-USD` — Refuse models that would exceed this estimated cost
- `X-Force-Tier` — Override classifier, use cheap/mid/frontier directly
- `X-Skip-Cache: true` — Bypass semantic cache
- `X-Cache-TTL` — Cache TTL in seconds (default: 86400)

### Model Tiers

- **cheap** — Default: `claude-haiku-4-5`. Also: `gpt-4o-mini`, `gemini-1.5-flash-8b`, `mistral-small-latest`
- **mid** — Default: `claude-sonnet-4-5`. Also: `gpt-4o-mini`, `gemini-1.5-flash`, `deepseek-chat`, `grok-2-mini`
- **frontier** — Default: `claude-opus-4-5`. Also: `gpt-4o`, `gemini-1.5-pro`, `grok-2`, `o3-mini`, `deepseek-reasoner`, `mistral-large-latest`

### Environment Variables

See `.env.example`. Only providers with keys configured are used — the router skips unavailable providers. Minimum viable setup: `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` (OpenAI key required for `text-embedding-3-small` semantic cache embeddings unless using a local embedding model).

### Docker Compose Services

- `postgres` — Must use `pgvector/pgvector:pg16` image (not plain postgres) for vector similarity search
- `redis` — Rate limiting + exact cache
- `proxy` — FastAPI on port 8000
- `dashboard` — React/Vite on port 3000
- `prometheus` — Metrics scraping on port 9090

### Middleware Order

FastAPI middleware stack is LIFO — register rate_limit first, auth second so auth runs first:
```python
app.middleware("http")(rate_limit_middleware)  # runs second
app.middleware("http")(api_key_middleware)     # runs first
```
