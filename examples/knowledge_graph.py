"""Knowledge graph operations with AutoGen and Dakera.

Demonstrates graph querying, traversal, and export.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python knowledge_graph.py
"""

import os

from autogen_dakera.knowledge_graph import DakeraKnowledgeGraph

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

kg = DakeraKnowledgeGraph(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-kg-demo",
)

print("--- Graph export ---")
graph = kg.export()
print(f"Nodes: {graph['node_count']}, Edges: {graph['edge_count']}")

print("\n--- Graph query ---")
results = kg.query(max_depth=3, limit=10)
print(f"Found {results['edge_count']} edges")
for edge in results["edges"][:5]:
    print(f"  {edge}")

print("\n--- Summarize ---")
try:
    summary = kg.summarize()
    print(f"Summary: {summary}")
except Exception as e:
    print(f"Summarize not supported on this server version: {e}")
