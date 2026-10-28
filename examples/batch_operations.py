"""Batch operations with AutoGen and Dakera.

Stores several memories, recalls for several queries at once and forgets them
in one call.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python batch_operations.py
"""

import os

from autogen_dakera import DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraMemory(
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
ids = [memory.add(item, importance=0.7)["id"] for item in items]
print(f"Stored {len(ids)} memories.")

print("\n--- Batch recall ---")
queries = ["shipping", "payment", "returns"]
results = memory.batch_query(queries, top_k=2)
for query, matches in zip(queries, results):
    print(f"\n  Query: '{query}'")
    for m in matches:
        print(f"    [{m['score']:.3f}] {m['content'][:50]}")

print("\n--- Batch forget ---")
memory.batch_forget(ids)
print(f"Forgot {len(ids)} memories.")
