-- migrations/004_security.sql
-- Rate limit config + request payload storage for replay

-- ── Per-client rate limit configuration ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS rate_limit_config (
    client_id           TEXT PRIMARY KEY,
    requests_per_minute INT  NOT NULL DEFAULT 60,
    requests_per_hour   INT  NOT NULL DEFAULT 1000,
    requests_per_day    INT  NOT NULL DEFAULT 10000,
    is_blocked          BOOLEAN NOT NULL DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Default entry — applies to any client not explicitly configured
INSERT INTO rate_limit_config (client_id, requests_per_minute, requests_per_hour, requests_per_day, notes)
VALUES ('default', 60, 1000, 10000, 'Global default limits')
ON CONFLICT (client_id) DO NOTHING;

-- ── Raw request payload storage (for replay) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS request_payloads (
    request_id      UUID PRIMARY KEY REFERENCES requests(request_id) ON DELETE CASCADE,
    messages        JSONB NOT NULL,
    request_params  JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payloads_created ON request_payloads (created_at DESC);
