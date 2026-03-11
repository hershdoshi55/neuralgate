"""
Day 5 cache tests — exact cache, semantic cache, and bypass.
Run from repo root: python tests/test_cache.py
Proxy must be running: uvicorn proxy.main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import time
import uuid
import httpx

BASE = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('PROXY_API_KEY', 'test-key')}",
}


def post(messages: list[dict], extra_headers: dict | None = None, model: str = "auto") -> dict:
    h = {**HEADERS, **(extra_headers or {})}
    r = httpx.post(
        f"{BASE}/v1/chat/completions",
        headers=h,
        json={"model": model, "messages": messages},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def show(label: str, resp: dict) -> None:
    ng = resp.get("x_neuralgate", {})
    print(f"\n[{label}]")
    print(f"  model        : {resp.get('model')}")
    print(f"  tier         : {ng.get('complexity_tier')}")
    print(f"  cache_hit    : {ng.get('cache_hit')}")
    print(f"  similarity   : {ng.get('cache_similarity')}")
    print(f"  latency_ms   : {ng.get('total_latency_ms')}")
    print(f"  answer       : {resp['choices'][0]['message']['content'][:100]!r}")


if __name__ == "__main__":
    run_id = uuid.uuid4().hex[:8]

    # ── Test 1: Exact cache ───────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 1: Exact cache (same request twice)")
    msg = [{"role": "user", "content": f"What is the speed of light? [run:{run_id}]"}]

    r1 = post(msg)
    show("1st call — LLM (should miss)", r1)
    assert not r1["x_neuralgate"]["cache_hit"], "Expected cache miss on first call"

    time.sleep(2)

    r2 = post(msg)
    show("2nd call — exact cache (should hit)", r2)
    assert r2["x_neuralgate"]["cache_hit"], "Expected cache HIT"
    assert r2["x_neuralgate"]["total_latency_ms"] < 200, "Cache hit should be <200ms"
    print("  PASS: exact cache working")

    # ── Test 2: Semantic cache ────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 2: Semantic cache (similar wording)")
    print("  Strategy: seed with X-Skip-Cache (forces LLM+store), then query with similar wording")

    seed_msg  = [{"role": "user", "content": f"What is the capital of France? [run:{run_id}]"}]
    query_msg = [{"role": "user", "content": f"Which city is the capital of France? [run:{run_id}]"}]

    # Seed: X-Skip-Cache bypasses the read so we always call LLM and store fresh
    r3 = post(seed_msg, extra_headers={"X-Skip-Cache": "true"})
    show("Seed call (X-Skip-Cache — guaranteed LLM)", r3)
    assert not r3["x_neuralgate"]["cache_hit"]

    time.sleep(4)  # wait for async embedding + pgvector store

    r4 = post(query_msg)
    show("Semantic query (similar wording — should hit)", r4)
    assert r4["x_neuralgate"]["cache_hit"], (
        f"Expected semantic cache HIT. similarity={r4['x_neuralgate'].get('cache_similarity')}"
    )
    print(f"  PASS: semantic cache hit (similarity={r4['x_neuralgate']['cache_similarity']:.4f})")

    # ── Test 3: Cache bypass ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 3: X-Skip-Cache bypass (even a cached prompt must call LLM)")
    r5 = post(seed_msg, extra_headers={"X-Skip-Cache": "true"})
    show("X-Skip-Cache on a cached prompt", r5)
    assert not r5["x_neuralgate"]["cache_hit"]
    print("  PASS: cache bypass working")

    # ── Test 4: Cheap tier (simple prompt) ────────────────────────────────
    print("\n" + "="*60)
    print("TEST 4: Cheap tier — simple factual question")
    r6 = post([{"role": "user", "content": "What color is the sky?"}])
    show("Simple question", r6)
    ng6 = r6["x_neuralgate"]
    if not ng6["cache_hit"]:
        assert ng6["complexity_tier"] == "cheap", f"Expected cheap tier, got {ng6['complexity_tier']}"
        print(f"  PASS: routed to cheap tier → {r6['model']}")
    else:
        print(f"  INFO: cache hit (tier not classified)")

    # ── Test 5: Frontier tier — forced via header ─────────────────────────
    print("\n" + "="*60)
    print("TEST 5: Frontier tier — forced via X-Force-Tier header")
    r7 = post(
        [{"role": "user", "content": "What color is the sky?"}],
        extra_headers={"X-Force-Tier": "frontier", "X-Skip-Cache": "true"},
    )
    show("Forced frontier tier", r7)
    ng7 = r7["x_neuralgate"]
    assert ng7["complexity_tier"] == "frontier", f"Expected frontier, got {ng7['complexity_tier']}"
    print(f"  PASS: forced to frontier → {r7['model']}")

    # ── Test 6: Frontier tier — complex prompt (auto-classified) ──────────
    print("\n" + "="*60)
    print("TEST 6: Frontier tier — complex prompt, auto-classified")
    complex_prompt = (
        "Design a distributed rate-limiting system for a multi-region API gateway. "
        "Include: (1) the data structures and algorithms for the sliding window counter, "
        "(2) how you handle clock skew across regions using vector clocks or hybrid logical clocks, "
        "(3) the Redis Lua script for atomic increment-and-check, "
        "(4) failure modes when Redis is partitioned and how to degrade gracefully, "
        "(5) the trade-offs between consistency and availability under CAP theorem for this use case."
    )
    r8 = post(
        [{"role": "user", "content": complex_prompt}],
        extra_headers={"X-Skip-Cache": "true"},
    )
    show("Complex prompt (auto-classify)", r8)
    ng8 = r8["x_neuralgate"]
    print(f"  complexity_score : {ng8.get('complexity_score')}")
    if ng8["complexity_tier"] == "frontier":
        print(f"  PASS: auto-classified as frontier → {r8['model']}")
    else:
        print(f"  INFO: classified as {ng8['complexity_tier']} → {r8['model']} (score: {ng8.get('complexity_score')})")

    # ── Test 7: Explicit model alias ──────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 7: Explicit alias — model='best' always uses frontier")
    r9 = post(
        [{"role": "user", "content": "Summarize the plot of Hamlet in one sentence."}],
        extra_headers={"X-Skip-Cache": "true"},
        model="best",
    )
    show("model='best'", r9)
    print(f"  model selected: {r9['model']}")

    print("\n" + "="*60)
    print("All tests done.")
