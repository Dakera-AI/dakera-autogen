"""Conversation history with AutoGen and Dakera.

Stores conversation turns as memories and retrieves relevant context
for follow-up questions — enabling long-term memory across sessions.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    export DAKERA_API_KEY="dk-..."          # optional
    pip install autogen-dakera
    python conversation_history.py
"""

import os

from autogen_dakera import DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraMemory(
    api_url=api_url,
    agent_id="autogen-chat-history",
    api_key=api_key,
    recall_k=5,
    importance=0.7,
)

turns = [
    ("Human: What's the capital of France?",
     "AI: The capital of France is Paris."),
    ("Human: What about Germany?",
     "AI: The capital of Germany is Berlin."),
    ("Human: Which one has a larger population?",
     "AI: Berlin has ~3.7M, Paris ~2.1M. Berlin is larger."),
    ("Human: I'm planning to visit the larger one.",
     "AI: Great choice! Berlin has amazing museums."),
]

print("Storing conversation turns...")
for human, ai in turns:
    memory.add(f"{human}\n{ai}")

print("\nRecalling context for 'travel plans':")
results = memory.query("travel plans")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:80]}...")

print("\nRecalling context for 'European capitals':")
results = memory.query("European capitals")
for r in results:
    print(f"  [{r['score']:.3f}] {r['content'][:80]}...")
