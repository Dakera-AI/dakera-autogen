"""Knowledge graph operations with AutoGen and Dakera.

Demonstrates graph querying, export and summarizing memories.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python knowledge_graph.py
"""

import os

from autogen_dakera.knowledge_graph import DakeraKnowledgeGraph
from autogen_dakera.memory import DakeraMemory

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
# Summarize needs the ids of at least two memories of this agent.
store = DakeraMemory(api_url=api_url, api_key=api_key, agent_id="autogen-kg-demo")
ids = [
    store.add("Anna leads the platform team in Berlin")["id"],
    store.add("Anna's platform team ships the Berlin release every Friday")["id"],
]
summary = kg.summarize(ids)
print(f"Summary of {summary['source_count']} memories: {summary['summary_memory']['content']}")
