from fastapi import APIRouter, Request, Query

router = APIRouter()


@router.get("/summary")
async def get_summary(request: Request, days: int = Query(default=7, ge=1, le=90)):
    """Overall cost, savings, latency, and cache stats for the period."""
    async with request.app.state.db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                                        AS total_requests,
                SUM(total_cost_usd)                                             AS total_cost,
                SUM(cost_savings_usd)                                           AS total_savings,
                AVG(total_latency_ms)                                           AS avg_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)  AS p95_latency,
                CASE WHEN COUNT(*) > 0
                     THEN SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*)
                     ELSE 0 END                                                 AS cache_hit_rate,
                SUM(CASE WHEN cache_hit THEN total_tokens ELSE 0 END)           AS tokens_saved_by_cache,
                SUM(CASE WHEN cache_hit THEN frontier_cost_usd ELSE 0 END)      AS cost_saved_by_cache
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

        tier_rows = await conn.fetch("""
            SELECT complexity_tier, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
              AND complexity_tier IS NOT NULL
            GROUP BY complexity_tier
            ORDER BY complexity_tier
        """, str(days))

        provider_rows = await conn.fetch("""
            SELECT selected_provider, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY selected_provider
            ORDER BY cost DESC NULLS LAST
        """, str(days))

        model_rows = await conn.fetch("""
            SELECT selected_model, COUNT(*) AS requests, SUM(total_cost_usd) AS cost
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY selected_model
            ORDER BY requests DESC
            LIMIT 10
        """, str(days))

    total_cost = float(stats["total_cost"] or 0)
    total_savings = float(stats["total_savings"] or 0)
    baseline = total_cost + total_savings

    return {
        "period_days": days,
        "total_requests": stats["total_requests"],
        "total_cost_usd": round(total_cost, 6),
        "total_savings_usd": round(total_savings, 6),
        "savings_percent": round(total_savings / baseline * 100, 1) if baseline > 0 else 0,
        "cache_hit_rate": round(float(stats["cache_hit_rate"] or 0), 3),
        "tokens_saved_by_cache": int(stats["tokens_saved_by_cache"] or 0),
        "avg_latency_ms": round(float(stats["avg_latency"] or 0)),
        "p95_latency_ms": round(float(stats["p95_latency"] or 0)),
        "by_tier": {
            row["complexity_tier"]: {
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 6),
            }
            for row in tier_rows
        },
        "by_provider": {
            row["selected_provider"]: {
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 6),
            }
            for row in provider_rows
        },
        "by_model": [
            {
                "model": row["selected_model"],
                "requests": row["requests"],
                "cost_usd": round(float(row["cost"] or 0), 6),
            }
            for row in model_rows
        ],
    }


@router.get("/routing")
async def get_routing(request: Request, days: int = Query(default=7, ge=1, le=90)):
    """Routing decision breakdown — tiers, models, failovers."""
    async with request.app.state.db_pool.acquire() as conn:
        tier_rows = await conn.fetch("""
            SELECT complexity_tier, COUNT(*) AS requests,
                   AVG(complexity_score)::float AS avg_score
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
              AND complexity_tier IS NOT NULL
            GROUP BY complexity_tier
            ORDER BY complexity_tier
        """, str(days))

        model_rows = await conn.fetch("""
            SELECT selected_model, selected_provider, complexity_tier,
                   COUNT(*) AS requests,
                   AVG(total_latency_ms)::float AS avg_latency_ms
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY selected_model, selected_provider, complexity_tier
            ORDER BY requests DESC
            LIMIT 15
        """, str(days))

        failover_count = await conn.fetchval("""
            SELECT COUNT(*) FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
              AND failover_occurred = TRUE
        """, str(days))

        total = await conn.fetchval("""
            SELECT COUNT(*) FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

    return {
        "period_days": days,
        "total_requests": total,
        "failover_count": failover_count,
        "failover_rate": round(failover_count / total, 3) if total else 0,
        "by_tier": [
            {
                "tier": row["complexity_tier"],
                "requests": row["requests"],
                "avg_complexity_score": round(row["avg_score"] or 0, 3),
                "percent": round(row["requests"] / total * 100, 1) if total else 0,
            }
            for row in tier_rows
        ],
        "by_model": [
            {
                "model": row["selected_model"],
                "provider": row["selected_provider"],
                "tier": row["complexity_tier"],
                "requests": row["requests"],
                "avg_latency_ms": round(row["avg_latency_ms"] or 0),
            }
            for row in model_rows
        ],
    }


@router.get("/savings")
async def get_savings(request: Request, days: int = Query(default=7, ge=1, le=90)):
    """Actual cost vs hypothetical all-frontier cost, broken down by day."""
    async with request.app.state.db_pool.acquire() as conn:
        totals = await conn.fetchrow("""
            SELECT
                SUM(total_cost_usd)    AS actual_cost,
                SUM(frontier_cost_usd) AS frontier_cost,
                SUM(cost_savings_usd)  AS total_savings
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

        daily_rows = await conn.fetch("""
            SELECT
                DATE(created_at AT TIME ZONE 'UTC') AS day,
                SUM(total_cost_usd)                  AS actual,
                SUM(frontier_cost_usd)               AS hypothetical,
                SUM(cost_savings_usd)                AS saved,
                COUNT(*)                             AS requests
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
            GROUP BY DATE(created_at AT TIME ZONE 'UTC')
            ORDER BY day ASC
        """, str(days))

    actual = float(totals["actual_cost"] or 0)
    frontier = float(totals["frontier_cost"] or 0)
    savings = float(totals["total_savings"] or 0)

    return {
        "period_days": days,
        "actual_cost_usd": round(actual, 6),
        "hypothetical_frontier_cost_usd": round(frontier, 6),
        "total_savings_usd": round(savings, 6),
        "savings_percent": round(savings / frontier * 100, 1) if frontier > 0 else 0,
        "daily_savings": [
            {
                "date": str(row["day"]),
                "actual": round(float(row["actual"] or 0), 6),
                "hypothetical": round(float(row["hypothetical"] or 0), 6),
                "saved": round(float(row["saved"] or 0), 6),
                "requests": row["requests"],
            }
            for row in daily_rows
        ],
    }


@router.get("/cache")
async def get_cache(request: Request, days: int = Query(default=7, ge=1, le=90)):
    """Cache hit rate, tokens saved, and cost saved by caching."""
    async with request.app.state.db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                                    AS total_requests,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)                 AS cache_hits,
                SUM(CASE WHEN cache_hit THEN total_tokens   ELSE 0 END)    AS tokens_saved,
                AVG(CASE WHEN cache_hit     THEN total_latency_ms END)     AS avg_cache_latency,
                AVG(CASE WHEN NOT cache_hit THEN total_latency_ms END)     AS avg_llm_latency
            FROM requests
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

        # Cost saved + semantic cache stats from semantic_cache table
        cache_type_rows = await conn.fetch("""
            SELECT
                COUNT(*)                  AS total_entries,
                SUM(hit_count)            AS total_hits,
                SUM(total_tokens_saved)   AS tokens_saved,
                SUM(total_cost_saved_usd) AS cost_saved
            FROM semantic_cache
            WHERE created_at > now() - ($1 || ' days')::interval
        """, str(days))

    total = int(stats["total_requests"] or 0)
    hits = int(stats["cache_hits"] or 0)

    return {
        "period_days": days,
        "total_requests": total,
        "cache_hits": hits,
        "cache_hit_rate": round(hits / total, 3) if total else 0,
        "tokens_saved": int(stats["tokens_saved"] or 0),
        "cost_saved_usd": round(float(cache_type_rows[0]["cost_saved"] or 0) if cache_type_rows else 0, 6),
        "avg_cache_latency_ms": round(float(stats["avg_cache_latency"] or 0)),
        "avg_llm_latency_ms": round(float(stats["avg_llm_latency"] or 0)),
        "semantic_cache": {
            "total_entries": int(cache_type_rows[0]["total_entries"] or 0) if cache_type_rows else 0,
            "total_hits": int(cache_type_rows[0]["total_hits"] or 0) if cache_type_rows else 0,
            "tokens_saved": int(cache_type_rows[0]["tokens_saved"] or 0) if cache_type_rows else 0,
            "cost_saved_usd": round(float(cache_type_rows[0]["cost_saved"] or 0), 6) if cache_type_rows else 0,
        },
    }


@router.get("/recent")
async def get_recent(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
):
    """Last N requests — used by the LiveRequestFeed in the dashboard."""
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                request_id, created_at, requested_model, selected_model,
                selected_provider, complexity_tier, complexity_score,
                prompt_tokens, completion_tokens, total_tokens,
                total_cost_usd, cost_savings_usd, frontier_cost_usd,
                cache_hit, cache_similarity, total_latency_ms,
                failover_occurred, finish_reason, client_id
            FROM requests
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

    return {
        "requests": [
            {
                "request_id": str(row["request_id"]),
                "created_at": row["created_at"].isoformat(),
                "requested_model": row["requested_model"],
                "selected_model": row["selected_model"],
                "selected_provider": row["selected_provider"],
                "complexity_tier": row["complexity_tier"],
                "complexity_score": float(row["complexity_score"]) if row["complexity_score"] else None,
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "total_cost_usd": float(row["total_cost_usd"] or 0),
                "cost_savings_usd": float(row["cost_savings_usd"] or 0),
                "cache_hit": row["cache_hit"],
                "cache_similarity": float(row["cache_similarity"]) if row["cache_similarity"] else None,
                "total_latency_ms": row["total_latency_ms"],
                "failover_occurred": row["failover_occurred"],
                "finish_reason": row["finish_reason"],
                "client_id": row["client_id"],
            }
            for row in rows
        ]
    }
