from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

# ── Metrics ───────────────────────────────────────────────────────────────────

request_counter = Counter(
    "neuralgate_requests_total",
    "Total proxy requests",
    ["model", "tier", "provider", "cache_hit"],
)

request_cost = Counter(
    "neuralgate_cost_usd_total",
    "Total cost in USD",
    ["model", "provider"],
)

request_latency = Histogram(
    "neuralgate_request_latency_ms",
    "End-to-end request latency in milliseconds",
    ["tier", "cache_hit"],
    buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000],
)

cache_hit_gauge = Gauge(
    "neuralgate_cache_hit_rate",
    "Rolling cache hit rate (last 100 requests)",
)

active_requests = Gauge(
    "neuralgate_active_requests",
    "Currently in-flight requests",
)


@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
