"""
NeuralGate benchmark — measures routing accuracy, latency, and cost.

Usage:
    python load-test/benchmark.py [--base URL] [--repeats N] [--concurrency N]

Defaults: base=http://localhost:8000, repeats=3, concurrency=5
"""
import asyncio
import httpx
import time
import statistics
import json
import argparse
from collections import Counter

BASE = "http://localhost:8000"

# Diverse prompts that span all three complexity tiers
TEST_PROMPTS = [
    # ── Cheap tier (score < 0.35) ──────────────────────────────────────────
    ("What is 2+2?", "cheap"),
    ("Define photosynthesis in one sentence.", "cheap"),
    ("What year was the Eiffel Tower built?", "cheap"),
    ("Translate 'hello' to French.", "cheap"),
    ("What is the capital of Japan?", "cheap"),

    # ── Mid tier (0.35 ≤ score < 0.65) ────────────────────────────────────
    ("Write a Python function to find the nth Fibonacci number.", "mid"),
    ("Summarize the key differences between REST and GraphQL in 3 bullet points.", "mid"),
    ("Explain how TCP/IP works in 3 paragraphs.", "mid"),

    # ── Frontier tier (score ≥ 0.65) ──────────────────────────────────────
    (
        "Analyze step by step the tradeoffs between different database indexing "
        "strategies for read-heavy vs write-heavy workloads. Include B-tree, "
        "hash, and GIN indexes. Consider cardinality, update frequency, and "
        "query pattern impacts.",
        "frontier",
    ),
    (
        "Critique and improve this algorithm, explain your reasoning:\n\n"
        "def sort(arr):\n"
        "    for i in range(len(arr)):\n"
        "        for j in range(len(arr)-1):\n"
        "            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]\n"
        "    return arr",
        "frontier",
    ),
]

HEADERS = {}  # Add "Authorization": "Bearer <key>" if auth is enabled


async def one_request(client: httpx.AsyncClient, prompt: str, expected_tier: str, skip_cache: bool = False) -> dict:
    t0 = time.monotonic()
    try:
        headers = {**HEADERS}
        if skip_cache:
            headers["X-Skip-Cache"] = "true"
        r = await client.post(
            "/v1/chat/completions",
            json={"model": "auto", "messages": [{"role": "user", "content": prompt}]},
            headers=headers,
            timeout=90.0,
        )
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        data = r.json()
        ng = data.get("x_neuralgate", {})
        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "latency_ms": elapsed_ms,
            "model": ng.get("selected_model", "unknown"),
            "tier": ng.get("complexity_tier"),
            "expected_tier": expected_tier,
            "correct_tier": ng.get("complexity_tier") == expected_tier,
            "cost_usd": ng.get("total_cost_usd", 0),
            "cache_hit": ng.get("cache_hit", False),
            "failover": ng.get("failover", False),
        }
    except Exception as e:
        return {
            "ok": False, "status": 0,
            "latency_ms": round((time.monotonic() - t0) * 1000),
            "model": None, "tier": None, "expected_tier": expected_tier,
            "correct_tier": False, "cost_usd": 0,
            "cache_hit": False, "failover": False,
            "error": str(e),
        }


async def run_benchmark(base: str, n_repeats: int, concurrency: int, skip_cache: bool = False):
    total = n_repeats * len(TEST_PROMPTS)
    print(f"\n{'='*60}")
    print(f"  NeuralGate Benchmark")
    print(f"  {n_repeats} passes × {len(TEST_PROMPTS)} prompts = {total} requests")
    print(f"  Concurrency: {concurrency}  |  Target: {base}")
    if skip_cache:
        print(f"  Cache: DISABLED (X-Skip-Cache: true — all requests hit LLMs)")
    print(f"{'='*60}\n")

    sem = asyncio.Semaphore(concurrency)

    async def bounded(client, prompt, tier):
        async with sem:
            return await one_request(client, prompt, tier, skip_cache=skip_cache)

    all_results = []
    async with httpx.AsyncClient(base_url=base) as client:
        for pass_num in range(1, n_repeats + 1):
            print(f"Pass {pass_num}/{n_repeats}...", end="", flush=True)
            tasks = [bounded(client, p, t) for p, t in TEST_PROMPTS]

            results = await asyncio.gather(*tasks)
            ok = sum(1 for r in results if r["ok"])
            cached = sum(1 for r in results if r["cache_hit"])
            print(f" {ok}/{len(results)} ok, {cached} cached")
            all_results.extend(results)

    # ── Compute stats ──────────────────────────────────────────────────────
    ok_results     = [r for r in all_results if r["ok"]]
    live_results   = [r for r in ok_results  if not r["cache_hit"]]
    cache_results  = [r for r in ok_results  if r["cache_hit"]]
    failed_results = [r for r in all_results if not r["ok"]]

    live_latencies = sorted(r["latency_ms"] for r in live_results)
    cache_latencies = sorted(r["latency_ms"] for r in cache_results)

    total_cost     = sum(r["cost_usd"] for r in ok_results)
    tier_correct   = sum(1 for r in ok_results if r["correct_tier"])
    failovers      = sum(1 for r in ok_results if r["failover"])

    def pct(n, d): return f"{n/d*100:.1f}%" if d else "n/a"
    def p(lst, percentile): return lst[int(len(lst) * percentile)] if lst else 0

    print(f"\n{'─'*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'─'*60}")
    print(f"  Total requests   : {len(all_results)}")
    print(f"  Successful       : {len(ok_results)} ({pct(len(ok_results), len(all_results))})")
    print(f"  Failed           : {len(failed_results)}")
    print(f"  Cache hits       : {len(cache_results)} ({pct(len(cache_results), len(ok_results))})")
    print(f"  Failovers        : {failovers}")
    print(f"  Tier accuracy    : {tier_correct}/{len(ok_results)} ({pct(tier_correct, len(ok_results))})")

    print(f"\n  LATENCY (live requests, n={len(live_latencies)})")
    if live_latencies:
        print(f"  P50  : {p(live_latencies, 0.50):,}ms")
        print(f"  P75  : {p(live_latencies, 0.75):,}ms")
        print(f"  P95  : {p(live_latencies, 0.95):,}ms")
        print(f"  P99  : {p(live_latencies, 0.99):,}ms")
        print(f"  Max  : {max(live_latencies):,}ms")
        print(f"  Mean : {int(statistics.mean(live_latencies)):,}ms")

    if cache_latencies:
        print(f"\n  LATENCY (cache hits, n={len(cache_latencies)})")
        print(f"  P50  : {p(cache_latencies, 0.50):,}ms")
        print(f"  P95  : {p(cache_latencies, 0.95):,}ms")

    # Pull cumulative savings from the analytics API
    routing_savings_pct = None
    routing_savings_usd = None
    hypothetical_usd = None
    cache_tokens_saved = None
    try:
        import httpx as _httpx
        r2 = _httpx.get(f"{base}/analytics/savings?days=1", timeout=5)
        if r2.status_code == 200:
            sv = r2.json()
            routing_savings_pct = sv.get("savings_percent")
            routing_savings_usd = sv.get("total_savings_usd")
            hypothetical_usd    = sv.get("hypothetical_frontier_cost_usd")
        r3 = _httpx.get(f"{base}/analytics/cache?days=1", timeout=5)
        if r3.status_code == 200:
            cache_tokens_saved = r3.json().get("tokens_saved")
    except Exception:
        pass

    print(f"\n  COST")
    print(f"  Actual total     : ${total_cost:.6f}")
    if ok_results:
        print(f"  Per request      : ${total_cost / len(ok_results):.8f}")
    if hypothetical_usd is not None and routing_savings_usd is not None:
        print(f"  All-frontier est.: ${hypothetical_usd:.6f}  (if every call used the best model)")
        saved_pct = f" ({routing_savings_pct}%)" if routing_savings_pct is not None else ""
        print(f"  Routing saved    : ${routing_savings_usd:.6f}{saved_pct}  ← from intelligent tier routing")
    if cache_results:
        cache_saved_usd = len(cache_results) * (total_cost / len(live_results)) if live_results else 0
        print(f"  Cache saved      : ${cache_saved_usd:.6f}  ({len(cache_results)} requests served free)")
    if cache_tokens_saved:
        print(f"  Tokens via cache : {cache_tokens_saved:,} tokens never sent to LLMs")

    model_dist = Counter(r["model"] for r in live_results if r["model"])
    if model_dist:
        print(f"\n  MODEL DISTRIBUTION (live requests)")
        for model, count in model_dist.most_common():
            print(f"  {model:<45} {count:>3} ({pct(count, len(live_results))})")

    tier_dist = Counter(r["tier"] for r in live_results if r["tier"])
    if tier_dist:
        print(f"\n  TIER DISTRIBUTION (live requests)")
        for tier in ["cheap", "mid", "frontier"]:
            count = tier_dist.get(tier, 0)
            print(f"  {tier:<10} {count:>3} ({pct(count, len(live_results))})")

    if failed_results:
        print(f"\n  ERRORS")
        for r in failed_results[:5]:
            print(f"  [{r['status']}] {r.get('error', 'HTTP error')}")

    print(f"\n{'='*60}\n")

    # Save JSON report
    report = {
        "total": len(all_results),
        "ok": len(ok_results),
        "failed": len(failed_results),
        "cache_hits": len(cache_results),
        "failovers": failovers,
        "tier_accuracy_pct": round(tier_correct / len(ok_results) * 100, 1) if ok_results else 0,
        "latency_p50_ms": p(live_latencies, 0.50),
        "latency_p95_ms": p(live_latencies, 0.95),
        "latency_p99_ms": p(live_latencies, 0.99),
        "total_cost_usd": round(total_cost, 8),
        "model_distribution": dict(model_dist),
        "tier_distribution": dict(tier_dist),
    }
    with open("load-test/benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("  Results saved to load-test/benchmark_results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuralGate benchmark")
    parser.add_argument("--base", default="http://localhost:8000", help="Proxy base URL")
    parser.add_argument("--repeats", type=int, default=3, help="Number of full passes")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent requests")
    parser.add_argument("--skip-cache", action="store_true", help="Send X-Skip-Cache: true to force LLM calls")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.base, args.repeats, args.concurrency, skip_cache=args.skip_cache))
