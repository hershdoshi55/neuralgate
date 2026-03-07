-- migrations/001_requests.sql

CREATE TABLE requests (
    -- ── Identity ─────────────────────────────────────────────────────────
    request_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ── Routing Decision ─────────────────────────────────────────────────
    requested_model     TEXT NOT NULL DEFAULT 'auto',
    selected_model      TEXT NOT NULL,
    selected_provider   TEXT NOT NULL,
    failover_occurred   BOOLEAN NOT NULL DEFAULT FALSE,
    original_model      TEXT,

    -- ── Complexity Classification ─────────────────────────────────────────
    complexity_score    DECIMAL(4,3),
    complexity_tier     TEXT,
    complexity_signals  JSONB,

    -- ── Token Counts ─────────────────────────────────────────────────────
    prompt_tokens       INT NOT NULL DEFAULT 0,
    completion_tokens   INT NOT NULL DEFAULT 0,
    total_tokens        INT GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,

    -- ── Cost ─────────────────────────────────────────────────────────────
    input_cost_usd      DECIMAL(12,8) NOT NULL DEFAULT 0,
    output_cost_usd     DECIMAL(12,8) NOT NULL DEFAULT 0,
    total_cost_usd      DECIMAL(12,8) GENERATED ALWAYS AS (input_cost_usd + output_cost_usd) STORED,

    frontier_cost_usd   DECIMAL(12,8),
    cost_savings_usd    DECIMAL(12,8) GENERATED ALWAYS AS
                        (COALESCE(frontier_cost_usd, 0) - (input_cost_usd + output_cost_usd)) STORED,

    -- ── Cache ─────────────────────────────────────────────────────────────
    cache_hit           BOOLEAN NOT NULL DEFAULT FALSE,
    cache_similarity    DECIMAL(5,4),

    -- ── Latency ──────────────────────────────────────────────────────────
    total_latency_ms    INT,
    provider_latency_ms INT,

    -- ── Request Content ──────────────────────────────────────────────────
    messages_hash       TEXT,
    message_count       INT NOT NULL DEFAULT 1,

    -- ── Response Metadata ────────────────────────────────────────────────
    finish_reason       TEXT,

    -- ── Client Context ────────────────────────────────────────────────────
    client_id           TEXT,

    -- ── Timestamps ───────────────────────────────────────────────────────
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX idx_requests_created ON requests (created_at DESC);
CREATE INDEX idx_requests_model ON requests (selected_model, created_at DESC);
CREATE INDEX idx_requests_provider ON requests (selected_provider, created_at DESC);
CREATE INDEX idx_requests_tier ON requests (complexity_tier, created_at DESC);
CREATE INDEX idx_requests_cache ON requests (cache_hit, created_at DESC);
CREATE INDEX idx_requests_client ON requests (client_id, created_at DESC)
    WHERE client_id IS NOT NULL;
CREATE INDEX idx_requests_cost ON requests (total_cost_usd DESC);
