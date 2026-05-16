"""DakeraSessionManager — conversation session tracking for AutoGen agents."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraSessionManager:
    """Manage conversation sessions for AutoGen agent memory grouping."""

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id
        self._active_session_id: str | None = None

    @property
    def active_session_id(self) -> str | None:
        return self._active_session_id

    def start(self, metadata: dict[str, Any] | None = None) -> str:
        """Start a new session. Returns session ID."""
        result = self._client.start_session(self._agent_id, metadata=metadata)
        self._active_session_id = result.session_id
        return result.session_id

    def end(self, summary: str | None = None) -> None:
        """End the active session."""
        if self._active_session_id is None:
            raise RuntimeError("No active session to end")
        self._client.end_session(self._active_session_id, summary=summary)
        self._active_session_id = None

    def get(self, session_id: str) -> dict[str, Any]:
        """Get session details."""
        result = self._client.get_session(session_id)
        return {
            "id": result.id, "agent_id": result.agent_id,
            "started_at": result.started_at, "ended_at": result.ended_at,
            "metadata": result.metadata, "memory_count": result.memory_count,
        }

    def list(self, active_only: bool = False) -> list[dict[str, Any]]:
        """List sessions."""
        result = self._client.list_sessions(self._agent_id, active_only=active_only)
        return [
            {"id": s.id, "started_at": s.started_at, "ended_at": s.ended_at,
             "memory_count": s.memory_count}
            for s in result.sessions
        ]

    def memories(self, session_id: str) -> list[dict[str, Any]]:
        """Get all memories from a session."""
        result = self._client.session_memories(session_id)
        return [{"id": m.id, "content": m.content, "importance": m.importance} for m in result.memories]

    def __enter__(self) -> DakeraSessionManager:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._active_session_id:
            self.end()
