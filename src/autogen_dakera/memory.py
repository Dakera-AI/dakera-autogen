"""DakeraMemory — AutoGen memory backed by the Dakera AI memory platform."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraMemory:
    """Persistent semantic memory for AutoGen agents backed by Dakera AI.

    Supports memory types, tags, TTL, batch operations, hybrid search,
    sessions, knowledge graph, and entity extraction.
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
    ) -> Any:
        """Store a memory with full parameter control."""
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
        """Semantic recall with optional filtering."""
        k = top_k if top_k is not None else self._recall_k
        min_imp = min_importance if min_importance is not None else (
            self._min_importance if self._min_importance > 0.0 else None
        )
        kwargs: dict[str, Any] = {"top_k": k}
        if min_imp:
            kwargs["min_importance"] = min_imp
        if tags:
            kwargs["tags"] = tags
        if memory_type:
            kwargs["memory_type"] = memory_type
        memories = self._client.recall(self._agent_id, query=query, **kwargs)
        return [
            {"content": m.content, "id": m.id, "score": m.score, "tags": m.tags}
            for m in memories.memories
        ]

    def hybrid_search(
        self,
        query: str,
        top_k: int | None = None,
        *,
        alpha: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Combined vector + BM25 search."""
        k = top_k if top_k is not None else self._recall_k
        result = self._client.search_memories(self._agent_id, query=query, top_k=k, alpha=alpha)
        return [{"content": m.content, "id": m.id, "score": m.score} for m in result.memories]

    def batch_query(self, queries: list[str], top_k: int | None = None) -> list[list[dict[str, Any]]]:
        """Run multiple queries in batch."""
        k = top_k if top_k is not None else self._recall_k
        results = []
        for q in queries:
            memories = self._client.recall(self._agent_id, query=q, top_k=k)
            results.append(
                [{"content": m.content, "id": m.id, "score": m.score} for m in memories.memories]
            )
        return results

    def forget(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._client.forget(self._agent_id, memory_id=memory_id)

    def batch_forget(self, memory_ids: list[str]) -> None:
        """Delete multiple memories."""
        self._client.batch_forget(self._agent_id, memory_ids=memory_ids)

    def update_importance(self, memory_id: str, importance: float) -> None:
        """Update a memory's importance score."""
        self._client.update_importance(self._agent_id, memory_id=memory_id, importance=importance)

    def consolidate(self) -> Any:
        """Deduplicate and consolidate memories."""
        return self._client.consolidate(self._agent_id)

    def stats(self) -> dict[str, Any]:
        """Get agent memory statistics."""
        return self._client.agent_stats(self._agent_id)

    def clear(self) -> None:
        """No-op: Dakera memories are persistent by design."""

    def __repr__(self) -> str:
        return (
            f"DakeraMemory(agent_id={self._agent_id!r}, "
            f"recall_k={self._recall_k}, min_importance={self._min_importance})"
        )
