"""Knowledge graph operations with AutoGen and Dakera.

Demonstrates linking memories, querying and exporting the graph, finding a path
and summarizing memories.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python knowledge_graph.py
"""

import os

from autogen_dakera import DakeraKnowledgeGraph, DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraMemory(api_url=api_url, api_key=api_key, agent_id="autogen-kg-demo")
kg = DakeraKnowledgeGraph(api_url=api_url, api_key=api_key, agent_id="autogen-kg-demo")

anna = memory.add("Anna leads the platform team in Berlin")["id"]
release = memory.add("Anna's platform team ships the Berlin release every Friday")["id"]
oncall = memory.add("The Berlin release needs an on-call engineer on Fridays")["id"]

print("--- Link memories ---")
link = kg.link(anna, release, label="team")
kg.link(release, oncall, label="release")
print(f"Linked {link['from_id']} -> {link['to_id']}")

print("\n--- Graph query ---")
results = kg.query(root_id=anna, max_depth=3, limit=10)
print(f"Found {results['edge_count']} edges")
for edge in results["edges"][:5]:
    print(f"  {edge['source']} -[{edge['type']}]-> {edge['target']}")

print("\n--- Path ---")
path = kg.find_path(anna, oncall)
print(f"{path['hop_count']} hops: {' -> '.join(path['path'])}")

print("\n--- Graph export ---")
graph = kg.export()
print(f"Nodes: {graph['node_count']}, Edges: {graph['edge_count']}")

print("\n--- Summarize ---")
# Summarize needs the ids of at least two memories of this agent; the summary is
# stored as a new memory.
summary = kg.summarize([anna, release])
print(f"Summary of {summary['source_count']} memories: {summary['summary_memory']['content']}")

# Forget what this demo stored, so a rerun starts from scratch.
memory.batch_forget([anna, release, oncall, summary["summary_memory"]["id"]])
