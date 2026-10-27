"""DakeraMemory — AutoGen memory backed by the Dakera AI memory platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dakera import DakeraClient


class DakeraMemory:
    """Synchronous access to an agent's Dakera memories, for tools and scripts.

    Store memories with memory types, tags, TTL, sessions and event time; recall
    them semantically with filters; search, consolidate and forget them. For the
    memory of an AutoGen agent (``AssistantAgent(memory=[...])``) use
    :class:`~autogen_dakera.DakeraAutoGenMemory`, which implements AutoGen's async
    ``Memory`` interface.

    Args:
        api_url: Dakera server URL.
        agent_id: The agent whose memories are read and written.
        api_key: Dakera API key.
        recall_k: Memories returned by :meth:`query` by default.
        min_importance: Default minimum importance of recalled memories.
        importance: Importance of memories stored by :meth:`add` by default.
    """

    def __init__(
        self,
        api_url: str,
        agent_id: str,
        api_key: str = "",
        recall_k: int = 5,
        min_importance: float = 0.0,
        importance: float = 0.7,
    ) -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id
        self._recall_k = recall_k
        self._min_importance = min_importance
        self._importance = importance

    def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        *,
        memory_type: str = "episodic",
        importance: float | None = None,
        tags: list[str] | None = None,
        ttl_seconds: int | None = None,
        session_id: str | None = None,
        event_time: int | float | str | datetime | None = None,
    ) -> Any:
        """Store a memory with full parameter control.

        ``event_time`` is when the memory's event happened (Unix seconds, an
        RFC 3339 string or a timezone-aware ``datetime``), for history written
        after the fact. Server v0.12.3+ reads it for recency and ``since`` /
        ``until``; ``created_at`` stays the ingest time.
        """
        kwargs: dict[str, Any] = {
            "memory_type": memory_type,
            "importance": importance if importance is not None else self._importance,
        }
        if metadata:
            kwargs["metadata"] = metadata
        if tags:
            kwargs["tags"] = tags
        if ttl_seconds is not None:
            kwargs["ttl_seconds"] = ttl_seconds
        if session_id:
            kwargs["session_id"] = session_id
        if event_time is not None:
            kwargs["event_time"] = event_time
        return self._client.store_memory(self._agent_id, content=content, **kwargs)

    def query(
        self,
        query: str,
        top_k: int | None = None,
        *,
        tags: list[str] | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic recall with optional filtering.

        Returns at most ``top_k`` ranked memories, most relevant first, as dicts
        with ``content``, ``id``, ``score`` (the server's ranking score),
        ``importance`` and ``metadata``. The server's neighbourhood context is
        requested separately and left out. ``tags`` matches memories carrying at
        least one of the tags.
        """
        k = top_k if top_k is not None else self._recall_k
        min_imp = (
            min_importance
            if min_importance is not None
            else (self._min_importance if self._min_importance > 0.0 else None)
        )
        kwargs: dict[str, Any] = {"top_k": k, "neighborhood_mode": "separate"}
        if min_imp:
            kwargs["min_importance"] = min_imp
        if tags:
            kwargs["tags"] = tags
        if memory_type:
            kwargs["memory_type"] = memory_type
        memories = self._client.recall(self._agent_id, query=query, **kwargs)
        return [
            {
                "content": m.content,
                "id": m.id,
                "score": m.score,
                "importance": m.importance,
                "metadata": m.metadata,
            }
            for m in memories.ranked[:k]
        ]

    def hybrid_search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Combined vector + BM25 search; dicts with ``content``, ``id`` and ``score``."""
        k = top_k if top_k is not None else self._recall_k
        results = self._client.search_memories(self._agent_id, query=query, top_k=k)
        return [
            {"content": m.get("content", ""), "id": m.get("id", ""), "score": m.get("score", 0.0)}
            for m in results
        ]

    def batch_query(
        self, queries: list[str], top_k: int | None = None
    ) -> list[list[dict[str, Any]]]:
        """Run multiple queries in batch (at most ``top_k`` ranked memories each)."""
        k = top_k if top_k is not None else self._recall_k
        results = []
        for q in queries:
            memories = self._client.recall(
                self._agent_id, query=q, top_k=k, neighborhood_mode="separate"
            )
            results.append(
                [{"content": m.content, "id": m.id, "score": m.score} for m in memories.ranked[:k]]
            )
        return results

    def forget(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._client.forget(self._agent_id, memory_id)

    def batch_forget(self, memory_ids: list[str]) -> None:
        """Delete multiple memories."""
        for mid in memory_ids:
            self._client.forget(self._agent_id, mid)

    def update_importance(self, memory_id: str, importance: float) -> None:
        """Update a memory's importance score."""
        self._client.update_importance(self._agent_id, [memory_id], importance)

    def consolidate(self, memory_ids: list[str] | None = None) -> Any:
        """Merge memories into one.

        ``memory_ids`` (at least two) picks the memories; without it the server
        picks up to five of the agent's most common memory type.
        """
        if memory_ids is None:
            return self._client.consolidate(self._agent_id)
        return self._client.consolidate(self._agent_id, memory_ids=memory_ids)

    def stats(self) -> dict[str, Any]:
        """Get the agent's memory statistics (``total_memories``, ...)."""
        return self._client.agent_stats(self._agent_id)

    def clear(self) -> None:
        """No-op: Dakera memories are persistent by design (use :meth:`forget`)."""

    def __repr__(self) -> str:
        return (
            f"DakeraMemory(agent_id={self._agent_id!r}, "
            f"recall_k={self._recall_k}, min_importance={self._min_importance})"
        )
