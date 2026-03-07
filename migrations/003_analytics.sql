-- migrations/003_analytics.sql

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

CREATE UNIQUE INDEX ON daily_analytics (day, selected_provider, selected_model, complexity_tier);
