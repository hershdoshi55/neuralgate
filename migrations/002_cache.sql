-- migrations/002_cache.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE semantic_cache (
    cache_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    messages_hash       TEXT UNIQUE NOT NULL,
    prompt_text         TEXT NOT NULL,
    prompt_embedding    vector(1536),
    response_text       TEXT NOT NULL,
    response_metadata   JSONB NOT NULL DEFAULT '{}',

    hit_count           INT NOT NULL DEFAULT 0,
    total_tokens_saved  INT NOT NULL DEFAULT 0,
    total_cost_saved_usd DECIMAL(12,8) NOT NULL DEFAULT 0,

    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_hit_at         TIMESTAMP WITH TIME ZONE,
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now() + INTERVAL '24 hours'
);

-- IVFFlat index for fast approximate nearest-neighbor search
CREATE INDEX ON semantic_cache
    USING ivfflat (prompt_embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE INDEX idx_cache_expires ON semantic_cache (expires_at);
CREATE INDEX idx_cache_hits ON semantic_cache (hit_count DESC);
