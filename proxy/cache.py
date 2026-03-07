# Stub cache — always returns no-hit. Full implementation in Day 5.

async def check_semantic_cache(messages_hash: str, full_text: str, db, redis):
    """Check L1 (Redis exact) then L2 (pgvector semantic) cache. Stub: always miss."""
    return None


async def store_semantic_cache(messages_hash: str, full_text: str, response_content: str,
                               response_metadata: dict, ttl_hours, db, redis):
    """Store response in cache. Stub: no-op until Day 5."""
    pass
