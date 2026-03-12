#!/usr/bin/env python3
"""
Day 7.5 test script — Auth, Rate Limiting, and Replay.
Run with: python test_day75.py
"""

import httpx
import time
import sys

BASE = "http://localhost:8000"
KEY  = "ng-17a918610455fefa277fa705ce63e55b4a4efebfb0e8e32dc645435eab61344a"
AUTH = {"Authorization": f"Bearer {KEY}"}
SIMPLE_PAYLOAD = {
    "model": "auto",
    "messages": [{"role": "user", "content": "What is 7 times 8?"}],
}

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m!\033[0m"

def check(label: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {icon} {label}{suffix}")
    return condition

def section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")

# ── 1. Auth ───────────────────────────────────────────────
section("1. AUTH")

r = httpx.post(f"{BASE}/v1/chat/completions", json=SIMPLE_PAYLOAD)
check("No key → 401", r.status_code == 401, f"got {r.status_code}")

r = httpx.post(f"{BASE}/v1/chat/completions", json=SIMPLE_PAYLOAD,
               headers={"Authorization": "Bearer wrong-key"})
check("Wrong key → 401", r.status_code == 401, f"got {r.status_code}")

r = httpx.post(f"{BASE}/v1/chat/completions", json=SIMPLE_PAYLOAD, headers=AUTH)
check("Correct key → 200", r.status_code == 200, f"got {r.status_code}")

r = httpx.get(f"{BASE}/metrics")
check("Public /metrics → 200 (no key)", r.status_code == 200, f"got {r.status_code}")

r = httpx.get(f"{BASE}/health")
check("Public /health → not 401", r.status_code != 401, f"got {r.status_code}")

# ── 2. Rate Limiting ──────────────────────────────────────
section("2. RATE LIMITING  (fires 65 rapid requests, limit=60/min)")

print(f"  Sending requests", end="", flush=True)
first_429 = None
statuses = []
# Use a fresh client-id so we don't collide with prior requests in this minute
client_id = f"test-rl-{int(time.time())}"

for i in range(1, 66):
    r = httpx.post(
        f"{BASE}/v1/chat/completions",
        json=SIMPLE_PAYLOAD,
        headers={**AUTH, "X-Client-ID": client_id, "X-Skip-Cache": "true"},
        timeout=15,
    )
    statuses.append(r.status_code)
    if r.status_code == 429 and first_429 is None:
        first_429 = i
    print("." if r.status_code == 200 else "X", end="", flush=True)

print()
check("Got a 429 before request 66", first_429 is not None,
      f"first 429 at request {first_429}" if first_429 else "never hit 429")
if first_429:
    check("429 hit between request 55–65", 55 <= first_429 <= 65,
          f"hit at {first_429} (expect ~61)")

# Check rate-limit headers on a fresh request
r = httpx.post(f"{BASE}/v1/chat/completions", json=SIMPLE_PAYLOAD, headers=AUTH)
has_headers = any(h.lower().startswith("x-ratelimit") for h in r.headers)
check("X-RateLimit-* headers present", has_headers,
      ", ".join(f"{k}: {v}" for k,v in r.headers.items() if "ratelimit" in k.lower()) or "none found")

# ── 3. End-to-end request check ───────────────────────────
section("3. END-TO-END REQUEST")

r = httpx.post(
    f"{BASE}/v1/chat/completions",
    json={"model": "auto", "messages": [{"role": "user", "content": "Name three planets in our solar system."}]},
    headers={**AUTH, "X-Skip-Cache": "true"},
    timeout=30,
)
check("Request succeeded", r.status_code == 200, f"got {r.status_code}")

if r.status_code == 200:
    ng = r.json().get("x_neuralgate", {})
    check("x_neuralgate block present", bool(ng))
    check("selected_model present", bool(ng.get("selected_model")))
    check("complexity_tier present", bool(ng.get("complexity_tier")))
    check("total_cost_usd present", ng.get("total_cost_usd") is not None)
    print(f"\n  model={ng['selected_model']} | tier={ng['complexity_tier']} | cost=${ng['total_cost_usd']:.6f} | latency={ng['total_latency_ms']}ms")

# ── Summary ───────────────────────────────────────────────
print(f"\n{'─'*55}")
print("  Done. Check http://localhost:3000 for the dashboard.")
print(f"{'─'*55}\n")
