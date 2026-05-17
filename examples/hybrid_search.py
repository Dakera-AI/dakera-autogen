"""Hybrid search (vector + BM25) with AutoGen and Dakera.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python hybrid_search.py
"""

import os

from autogen_dakera.memory import DakeraAutogenMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

store = DakeraAutogenMemory(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-hybrid-demo",
    namespace="docs",
)

documents = [
    "Python is a high-level programming language.",
    "Rust provides memory safety without garbage collection.",
    "TypeScript adds static types to JavaScript.",
    "Go is designed for concurrent systems programming.",
    "FastAPI is a modern Python web framework.",
]

print("Indexing documents...")
store.add_texts(documents)

print("\n--- Vector search ---")
results = store.search("memory safe language", top_k=3)
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:60]}")

print("\n--- Hybrid search ---")
results = store.hybrid_search("Python web", top_k=3, alpha=0.5)
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:60]}")
