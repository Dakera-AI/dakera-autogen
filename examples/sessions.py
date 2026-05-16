"""Session-scoped memory with AutoGen and Dakera.

Demonstrates starting a session, storing memories within it,
and ending with a summary.

Usage:
    export DAKERA_API_URL="http://localhost:3300"
    python sessions.py
"""

import os

from autogen_dakera.sessions import DakeraSessionManager

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3300")
api_key = os.environ.get("DAKERA_API_KEY", "")

sessions = DakeraSessionManager(
    api_url=api_url,
    api_key=api_key,
    agent_id="autogen-session-demo",
)

session_id = sessions.start(metadata={"topic": "onboarding"})
print(f"Started session: {session_id}")

# Store memories within the session context
sessions.store(session_id, "User asked about password reset", importance=0.8)
sessions.store(session_id, "User asked about API keys", importance=0.7)

memories = sessions.memories(session_id)
print(f"\nMemories in session: {len(memories)}")
for m in memories:
    print(f"  - {m['content'][:60]}")

sessions.end(summary="Helped with account setup")
print("\nSession ended.")
