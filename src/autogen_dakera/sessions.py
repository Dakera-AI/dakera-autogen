"""DakeraSessionManager — conversation session tracking for AutoGen agents."""

from __future__ import annotations

import builtins
from typing import Any

from dakera import DakeraClient

# Tag of the sentence sub-memories the server derives from a stored memory.
_DERIVED_TAG = "dakera-curated"


class DakeraSessionManager:
    """Group an agent's memories into conversation sessions.

    Pass :attr:`active_session_id` as ``session_id`` when storing memories to
    attach them to the session. Usable as a context manager: ``with sessions:``
    starts a session and ends it on exit.

    Args:
        api_url: Dakera server URL.
        agent_id: The agent the sessions belong to.
        api_key: Dakera API key.
    """

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id
        self._active_session_id: str | None = None

    @property
    def active_session_id(self) -> str | None:
        """The session started by :meth:`start` and not yet ended, if any."""
        return self._active_session_id

    def start(
        self, metadata: dict[str, Any] | None = None, *, idle_timeout_secs: int | None = None
    ) -> str:
        """Start a new session. Returns session ID.

        The server ends a session after a period without activity (default
        4 h). ``idle_timeout_secs`` sets this session's own timeout (``0`` =
        never); keep a long-lived session open with :meth:`touch`.
        """
        if idle_timeout_secs is None:
            result = self._client.start_session(self._agent_id, metadata=metadata)
        else:
            result = self._client.start_session(
                self._agent_id, metadata=metadata, idle_timeout_secs=idle_timeout_secs
            )
        session_id: str = result["id"]
        self._active_session_id = session_id
        return session_id

    def touch(self) -> dict[str, Any]:
        """Record activity on the active session so it does not end for inactivity.

        Returns ``{"session_state", "idle_deadline_at"}``; ``session_state`` is
        ``"ended"`` when the server already ended the session.
        """
        if self._active_session_id is None:
            raise RuntimeError("No active session to touch")
        result = self._client.touch_session(self._active_session_id)
        return {
            "session_state": result.session_state,
            "idle_deadline_at": result.idle_deadline_at,
        }

    def end(self) -> None:
        """End the active session."""
        if self._active_session_id is None:
            raise RuntimeError("No active session to end")
        self._client.end_session(self._active_session_id)
        self._active_session_id = None

    def get(self, session_id: str) -> dict[str, Any]:
        """Get a session's details.

        ``ended_reason`` says why an ended session ended (``"client"``, ``"idle"``, ...).
        """
        result = self._client.get_session(session_id)
        return {
            "id": result.get("id", session_id),
            "agent_id": result.get("agent_id", ""),
            "started_at": result.get("started_at"),
            "ended_at": result.get("ended_at"),
            "metadata": result.get("metadata"),
            "memory_count": result.get("memory_count", 0),
            "ended_reason": result.get("ended_reason"),
            "last_activity_at": result.get("last_activity_at"),
        }

    def list(self, active_only: bool = False) -> list[dict[str, Any]]:
        """List the agent's sessions, optionally only those still active."""
        result: Any = self._client.list_sessions(self._agent_id, active_only=active_only)
        # The server answers ``{"sessions": [...], "total": n}``; the SDK
        # passes that object through, so take the list out of it.
        sessions = result.get("sessions", []) if isinstance(result, dict) else result
        return [
            {
                "id": s.get("id", ""),
                "started_at": s.get("started_at"),
                "ended_at": s.get("ended_at"),
                "memory_count": s.get("memory_count", 0),
                "ended_reason": s.get("ended_reason"),
            }
            for s in sessions
        ]

    def memories(
        self, session_id: str, *, include_derived: bool = False
    ) -> builtins.list[dict[str, Any]]:
        """Get the memories stored in a session, oldest first.

        The server also lists the sentence sub-memories it derives from them
        (tagged ``dakera-curated``); they are left out unless ``include_derived=True``.
        """
        mems = self._client.session_memories(session_id)
        if not include_derived:
            mems = [m for m in mems if _DERIVED_TAG not in (m.get("tags") or [])]
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
