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
        session_id: str = result["id"]
        self._active_session_id = session_id
        return session_id

    def end(self) -> None:
        """End the active session."""
        if self._active_session_id is None:
            raise RuntimeError("No active session to end")
        self._client.end_session(self._active_session_id)
        self._active_session_id = None

    def get(self, session_id: str) -> dict[str, Any]:
        """Get session details."""
        result = self._client.get_session(session_id)
        return {
            "id": result.get("id", session_id),
            "agent_id": result.get("agent_id", ""),
            "started_at": result.get("started_at"),
            "ended_at": result.get("ended_at"),
            "metadata": result.get("metadata"),
            "memory_count": result.get("memory_count", 0),
        }

    def list(self, active_only: bool = False) -> list[dict[str, Any]]:
        """List sessions."""
        sessions = self._client.list_sessions(self._agent_id, active_only=active_only)
        return [
            {
                "id": s.get("id", ""),
                "started_at": s.get("started_at"),
                "ended_at": s.get("ended_at"),
                "memory_count": s.get("memory_count", 0),
            }
            for s in sessions
        ]

    def memories(self, session_id: str) -> list[dict[str, Any]]:
        """Get all memories from a session."""
        mems = self._client.session_memories(session_id)
        return [
            {
                "id": m.get("id", ""),
                "content": m.get("content", ""),
                "importance": m.get("importance", 0.0),
            }
            for m in mems
        ]

    def __enter__(self) -> DakeraSessionManager:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._active_session_id:
            self.end()
