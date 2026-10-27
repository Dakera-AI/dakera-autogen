"""Basic agent memory with AutoGen and Dakera.

DakeraMemory is the synchronous API to an agent's memories, for tools and
scripts; memories survive across processes and runs. For the memory of an AutoGen
AssistantAgent, see assistant_agent.py.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install autogen-dakera
    python basic_memory.py
"""

import os

from autogen_dakera import DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraMemory(
    api_url=api_url,
    agent_id="autogen-assistant",
    api_key=api_key,
    recall_k=3,
    importance=0.8,
)

ids = [
    memory.add("User is building a chatbot for customer support.")["id"],
    memory.add("The chatbot should handle returns, refunds, and order tracking.")["id"],
    memory.add("Preferred tech stack: Python backend, React frontend.")["id"],
]

print("Querying 'what is the user building?':")
results = memory.query("what is the user building?")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

print("\nQuerying 'technology stack':")
results = memory.query("technology stack")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

# Forget what this demo stored, so a rerun starts from scratch.
memory.batch_forget(ids)
