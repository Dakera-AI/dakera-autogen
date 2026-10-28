"""Advanced memory features with AutoGen and Dakera.

Demonstrates importance levels, filtered recall, event time and consolidation.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python advanced_memory.py
"""

import os

from autogen_dakera import DakeraMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

memory = DakeraMemory(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-advanced-demo",
)

print("--- Different importance levels ---")
ids = [
    memory.add("casual greeting", importance=0.3)["id"],
    memory.add("user is allergic to peanuts", importance=0.95)["id"],
    memory.add("birthday is March 15", importance=0.8, tags=["personal"])["id"],
]

print("--- High-importance recall ---")
results = memory.query("user allergy and birthday", min_importance=0.7)
for r in results:
    print(f"  [{r['importance']:.1f}] {r['content']}")

print("--- Tag-filtered recall ---")
for r in memory.query("birthday", tags=["personal"]):
    print(f"  {r['content']}")

print("--- Event time (server v0.12.3+) ---")
# A memory written after the fact keeps when its event happened; recency and
# since/until read it, while created_at stays the ingest time.
stored = memory.add("user moved to Berlin", event_time="2021-06-01T00:00:00Z")
ids.append(stored["id"])
print(f"  event time: {stored['metadata']['_dakera_event_time']}")

print("--- Consolidation ---")
# Merge exactly these memories into one (the originals are replaced by it).
merged = memory.consolidate(
    [
        memory.add("user drinks oat milk")["id"],
        memory.add("user drinks oat milk in coffee every morning")["id"],
    ]
)
ids.append(merged["consolidated_memory"]["id"])
print(f"  merged {len(merged['source_memory_ids'])} memories into one")

# Forget what this demo stored, so a rerun starts from scratch.
memory.batch_forget(ids)
