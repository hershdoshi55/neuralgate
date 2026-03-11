import asyncio
import json

from openai import AsyncOpenAI
from proxy.settings import settings

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _embed(text: str) -> list[float]:
    """Generate embedding via OpenAI text-embedding-3-small."""
    resp = await _get_openai_client().embeddings.create(
        model=settings.embedding_model,
        input=text[:8000],
    )
    return resp.data[0].embedding


async def check_semantic_cache(
    messages_hash: str,
    full_text: str,
    db,
    redis,
) -> dict | None:
    """
    L1: exact Redis match (zero embedding overhead).
    L2: pgvector cosine similarity search.
    Returns cached response dict or None on miss.
    """
    # ── L1: Exact match ───────────────────────────────────────────────────
    exact_key = f"cache:exact:{messages_hash}"
    raw = await redis.get(exact_key)
    if raw:
        cached = json.loads(raw)
        asyncio.create_task(_increment_hits(messages_hash, cached, db))
        return {**cached, "similarity": 1.0, "cache_type": "exact"}

    # ── L2: Semantic match ────────────────────────────────────────────────
    try:
        embedding = await _embed(full_text)
    except Exception as e:
        print(f"Cache embed error: {e}")
        return None

    try:
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    messages_hash,
                    response_text,
                    response_metadata,
                    1 - (prompt_embedding <=> $1::vector) AS similarity
                FROM semantic_cache
                WHERE expires_at > now()
                  AND 1 - (prompt_embedding <=> $1::vector) >= $2
                ORDER BY prompt_embedding <=> $1::vector
                LIMIT 1
                """,
                str(embedding),
                settings.cache_similarity_threshold,
            )
    except Exception as e:
        print(f"Cache pgvector query error: {e}")
        return None

    if not row:
        return None

    similarity = float(row["similarity"])
    # asyncpg may return JSONB as dict or string depending on version
    metadata = row["response_metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    cache_data = {
        "content": row["response_text"],
        "model": metadata.get("model", "cached"),
        "completion_tokens": metadata.get("completion_tokens", 0),
        "finish_reason": metadata.get("finish_reason", "stop"),
        "cache_type": "semantic",
        "similarity": similarity,
    }

    # Promote to L1 so the next identical request skips embedding
    await redis.setex(exact_key, 3600, json.dumps(cache_data))
    asyncio.create_task(_increment_hits(row["messages_hash"], metadata, db))

    return cache_data


async def store_semantic_cache(
    messages_hash: str,
    full_text: str,
    response_content: str,
    response_metadata: dict,
    ttl_hours,
    db,
    redis,
) -> None:
    """Store a prompt+response in pgvector and Redis. Non-fatal on failure."""
    ttl = ttl_hours or settings.default_cache_ttl_hours

    try:
        embedding = await _embed(full_text)
    except Exception as e:
        print(f"Cache store embed error: {e}")
        return

    cache_data = {
        "content": response_content,
        "model": response_metadata.get("model", "unknown"),
        "completion_tokens": response_metadata.get("completion_tokens", 0),
        "finish_reason": response_metadata.get("finish_reason", "stop"),
    }

    try:
        async with db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO semantic_cache
                    (messages_hash, prompt_text, prompt_embedding, response_text,
                     response_metadata, expires_at)
                VALUES ($1, $2, $3::vector, $4, $5::jsonb,
                        now() + $6 * interval '1 hour')
                ON CONFLICT (messages_hash) DO UPDATE
                    SET response_text     = EXCLUDED.response_text,
                        response_metadata = EXCLUDED.response_metadata,
                        expires_at        = EXCLUDED.expires_at
                """,
                messages_hash,
                full_text[:5000],
                str(embedding),
                response_content,
                json.dumps(response_metadata),
                float(ttl),
            )
    except Exception as e:
        print(f"Cache pgvector store error: {e}")
        return

    try:
        await redis.setex(
            f"cache:exact:{messages_hash}",
            int(ttl * 3600),
            json.dumps(cache_data),
        )
    except Exception as e:
        print(f"Cache Redis store error: {e}")


async def _increment_hits(messages_hash: str, metadata: dict, db) -> None:
    try:
        tokens_saved = (metadata.get("prompt_tokens") or 0) + (metadata.get("completion_tokens") or 0)
        cost_saved = (metadata.get("input_cost_usd") or 0) + (metadata.get("output_cost_usd") or 0)
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE semantic_cache
                SET hit_count           = hit_count + 1,
                    last_hit_at         = now(),
                    total_tokens_saved  = total_tokens_saved + $2,
                    total_cost_saved_usd = total_cost_saved_usd + $3
                WHERE messages_hash = $1
                """,
                messages_hash,
                tokens_saved,
                cost_saved,
            )
    except Exception:
        pass
