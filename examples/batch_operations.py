"""Batch operations with AutoGen and Dakera.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python batch_operations.py
"""

import os

from autogen_dakera import DakeraAutogenMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraAutogenMemory(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-batch-demo",
)

print("Storing batch of memories...")
items = [
    "30-day return policy for unopened items.",
    "International shipping to 40+ countries.",
    "Accepts Visa, Mastercard, and PayPal.",
    "Loyalty program: 1 point per dollar.",
    "Gift cards: $25, $50, $100 denominations.",
]
for item in items:
    memory.store(item, importance=0.7)
print(f"Stored {len(items)} memories.")

print("\n--- Batch recall ---")
queries = ["shipping", "payment", "returns"]
results = memory.batch_search(queries, limit=2)
for query, matches in zip(queries, results):
    print(f"\n  Query: '{query}'")
    for m in matches:
        print(f"    [{m['importance']:.1f}] {m['content'][:50]}")
