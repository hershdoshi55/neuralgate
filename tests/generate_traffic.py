"""Generate test traffic for analytics. Run: python tests/generate_traffic.py"""
import httpx

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

prompts = [
    ("auto", "What is 1 + 1?"),
    ("auto", "What is 2 + 2?"),
    ("auto", "What color is the sky?"),
    ("auto", "What is the capital of Japan?"),
    ("auto", "How do you boil water?"),
    ("auto", "What is 10 * 10?"),
    ("auto", "What is the speed of sound?"),
    ("auto", "Who invented the telephone?"),
    ("auto", "What is the largest planet?"),
    ("auto", "What year did WW2 end?"),
    ("cheapest", "Translate 'hello' to Spanish."),
    ("cheapest", "What is 7 * 8?"),
    ("balanced", "Explain what a REST API is in 2 sentences."),
    ("balanced", "What is the difference between TCP and UDP?"),
    ("balanced", "Explain what a database index does."),
    ("best", "What are the pros and cons of microservices architecture?"),
    ("best", "Explain the CAP theorem."),
    ("auto", "What is Python?"),
    ("auto", "What is the boiling point of water in Fahrenheit?"),
    ("auto", "What is 100 / 4?"),
]

for i, (model, content) in enumerate(prompts, 1):
    try:
        r = httpx.post(
            f"{BASE}/v1/chat/completions",
            headers=HEADERS,
            json={"model": model, "messages": [{"role": "user", "content": content}]},
            timeout=30,
        )
        ng = r.json().get("x_neuralgate", {})
        tier = ng.get('complexity_tier') or '?'
        print(f"[{i:2d}] {model:<10} tier={tier:<9} "
              f"cache={str(ng.get('cache_hit')):<5} model={r.json().get('model','?')}")
    except Exception as e:
        print(f"[{i:2d}] ERROR: {e}")

print("\nDone. Run: curl -s http://localhost:8000/analytics/summary | python3 -m json.tool")
