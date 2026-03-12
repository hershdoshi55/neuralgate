import time
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

PUBLIC_ROUTES = {"/health", "/metrics"}

DEFAULT_LIMITS = {
    "minute": 60,
    "hour":   1000,
    "day":    10000,
}

WINDOW_SECONDS = {
    "minute": 60,
    "hour":   3600,
    "day":    86400,
}


async def get_client_limits(client_id: str, db) -> dict | None:
    """Fetch per-client limits from Postgres. Returns None if client is hard-blocked."""
    try:
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT requests_per_minute, requests_per_hour, requests_per_day, is_blocked "
                "FROM rate_limit_config WHERE client_id = $1 OR client_id = 'default' "
                "ORDER BY (client_id = $1) DESC LIMIT 1",
                client_id,
            )
            if row:
                if row["is_blocked"]:
                    return None
                return {
                    "minute": row["requests_per_minute"],
                    "hour":   row["requests_per_hour"],
                    "day":    row["requests_per_day"],
                }
    except Exception:
        pass
    return DEFAULT_LIMITS


async def check_rate_limit(client_id: str, redis: aioredis.Redis, db) -> tuple[bool, dict]:
    """
    Sliding window rate limit check using Redis sorted sets.
    Returns (allowed, info_dict).
    """
    limits = await get_client_limits(client_id, db)

    if limits is None:
        return False, {"reason": "client_blocked", "retry_after": 3600}

    now = int(time.time())
    results = {}

    for window_name, limit in limits.items():
        window_secs = WINDOW_SECONDS[window_name]
        redis_key = f"ratelimit:{client_id}:{window_name}"

        pipe = redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_secs)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {f"{now}:{id(pipe)}": now})
        pipe.expire(redis_key, window_secs + 1)
        _, count, _, _ = await pipe.execute()

        results[window_name] = {
            "count":      count,
            "limit":      limit,
            "remaining":  max(0, limit - count),
            "resets_at":  now + window_secs,
        }

        if count >= limit:
            return False, {
                "reason":      f"rate_limit_exceeded_{window_name}",
                "retry_after": window_secs,
                "window":      window_name,
                "limit":       limit,
                "current":     count,
                "all_windows": results,
            }

    return True, {"all_windows": results}


async def rate_limit_middleware(request: Request, call_next):
    """
    Enforce per-client sliding-window rate limits.
    Runs AFTER auth middleware (FastAPI LIFO — register this first).
    """
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    client_id = request.headers.get("X-Client-ID")
    if not client_id:
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
                    "message":     f"Rate limit exceeded. {info.get('reason', '')}",
                    "type":        "rate_limit_exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "code":        429,
                    "details":     info,
                }
            },
        )

    request.state.rate_limit_info = info
    response = await call_next(request)

    minute_info = info.get("all_windows", {}).get("minute", {})
    response.headers["X-RateLimit-Limit"]     = str(minute_info.get("limit", 60))
    response.headers["X-RateLimit-Remaining"] = str(minute_info.get("remaining", 0))
    response.headers["X-RateLimit-Reset"]     = str(minute_info.get("resets_at", 0))

    return response
