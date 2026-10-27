"""Hybrid search (vector + BM25) with AutoGen and Dakera.

query() is semantic recall; hybrid_search() also matches the words of the query.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python hybrid_search.py
"""

import os

from autogen_dakera import DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

store = DakeraMemory(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-hybrid-demo",
)

documents = [
    "Python is a high-level programming language.",
    "Rust provides memory safety without garbage collection.",
    "TypeScript adds static types to JavaScript.",
    "Go is designed for concurrent systems programming.",
    "FastAPI is a modern Python web framework.",
]

print("Indexing documents...")
ids = [store.add(doc)["id"] for doc in documents]

print("\n--- Semantic recall ---")
results = store.query("memory safe language", top_k=3)
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:60]}")

print("\n--- Hybrid search ---")
results = store.hybrid_search("Python web", top_k=3)
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:60]}")

# Forget what this demo stored, so a rerun starts from scratch.
store.batch_forget(ids)
