"""Session-scoped memory with AutoGen and Dakera.

Demonstrates starting a session, storing memories in it, keeping it open while
idle and ending it.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    python sessions.py
"""

import os

from autogen_dakera import DakeraMemory, DakeraSessionManager

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")

sessions = DakeraSessionManager(api_url=api_url, api_key=api_key, agent_id="autogen-session-demo")
memory = DakeraMemory(api_url=api_url, api_key=api_key, agent_id="autogen-session-demo")

# The server ends a session after 4 h without activity by default (server v0.12.2+);
# idle_timeout_secs sets this session's own timeout.
session_id = sessions.start(metadata={"topic": "onboarding"}, idle_timeout_secs=3600)
print(f"Started session: {session_id}")

# Store memories in the session
ids = [
    memory.add("User asked about password reset", importance=0.8, session_id=session_id)["id"],
    memory.add("User asked about API keys", importance=0.7, session_id=session_id)["id"],
]

memories = sessions.memories(session_id)
print(f"\nMemories in session: {len(memories)}")
for m in memories:
    print(f"  - {m['content'][:60]}")

# A long-running conversation records activity so the session is not ended.
print(f"\nSession state after touch: {sessions.touch()['session_state']}")

sessions.end()
print(f"Session ended ({sessions.get(session_id)['ended_reason']}).")

# The context-manager form starts a session and ends it on exit.
with sessions:
    ids.append(memory.add("User enabled 2FA", session_id=sessions.active_session_id)["id"])

# Forget what this demo stored, so a rerun starts from scratch.
memory.batch_forget(ids)
