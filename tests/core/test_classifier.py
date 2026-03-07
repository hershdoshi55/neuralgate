# test_classifier.py
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from proxy.classifier import classify_complexity

test_cases = [
    # Expected cheap
    ([{"role": "user", "content": "What is 2+2?"}], "cheap"),
    ([{"role": "user", "content": "What is the capital of France?"}], "cheap"),
    ([{"role": "user", "content": "Translate 'hello' to Spanish"}], "cheap"),
    ([{"role": "user", "content": "Define recursion"}], "cheap"),

    # Expected mid
    ([{"role": "user", "content": "Summarize the key points of machine learning in 3 paragraphs"}], "mid"),
    ([{"role": "user", "content": "Write a Python function to merge two sorted lists"}], "mid"),
    ([{"role": "user", "content": "Compare React and Vue.js for a large-scale application"}], "mid"),

    # Expected frontier
    ([{"role": "user", "content": "Analyze the macroeconomic implications of quantitative easing on emerging market debt"}], "frontier"),
    ([{"role": "user", "content": "Review and critique this code, explain step by step what's wrong and how to optimize it: " + "def fib(n):\n  if n<=1: return n\n  return fib(n-1)+fib(n-2)"}], "frontier"),
    ([{"role": "user", "content": "Write a persuasive essay arguing for and against universal basic income, synthesizing economic research"}], "frontier"),
]

print("Classifier Test Results:")
print("=" * 80)
correct = 0
for messages, expected in test_cases:
    result = classify_complexity(messages)
    status = "✓" if result["tier"] == expected else "✗"
    if result["tier"] == expected:
        correct += 1
    print(f"{status} Score: {result['score']:.2f} | Tier: {result['tier']:8s} | Expected: {expected:8s}")
    print(f"  Prompt: {messages[0]['content'][:60]!r}...")
    print(f"  Signals: {result['signals'][:3]}")
    print()

print(f"Accuracy: {correct}/{len(test_cases)} = {correct/len(test_cases)*100:.0f}%")
