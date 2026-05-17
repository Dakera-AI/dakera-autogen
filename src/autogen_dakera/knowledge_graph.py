"""DakeraKnowledgeGraph — knowledge graph operations for AutoGen agents."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraKnowledgeGraph:
    """Knowledge graph for entity relationships in AutoGen workflows."""

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id

    def query(
        self,
        root_id: str | None = None,
        edge_type: str | None = None,
        max_depth: int = 3,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Query the knowledge graph."""
        result = self._client.knowledge_query(
            self._agent_id, root_id=root_id, edge_type=edge_type, max_depth=max_depth, limit=limit
        )
        return {
            "edges": [{"source": e.source_id, "target": e.target_id, "type": e.edge_type} for e in result.edges],
            "node_count": result.node_count,
            "edge_count": result.edge_count,
        }

    def find_path(self, from_id: str, to_id: str) -> dict[str, Any]:
        """Find shortest path between two memory nodes."""
        result = self._client.knowledge_path(self._agent_id, from_id=from_id, to_id=to_id)
        return {"path": result.path, "hop_count": result.hop_count}

    def link(self, source_id: str, target_id: str, edge_type: str = "linked_by") -> None:
        """Link two memories in the knowledge graph."""
        self._client.memory_link(source_id, target_id, edge_type=edge_type)

    def export(self) -> dict[str, Any]:
        """Export the full knowledge graph."""
        result = self._client.knowledge_export(self._agent_id)
        return {
            "edges": [{"source": e.source_id, "target": e.target_id, "type": e.edge_type} for e in result.edges],
            "node_count": result.node_count,
            "edge_count": result.edge_count,
        }

    def build(self, memory_id: str | None = None, depth: int | None = None) -> dict[str, Any]:
        """Build/rebuild the knowledge graph from memories."""
        return self._client.knowledge_graph(self._agent_id, memory_id=memory_id, depth=depth)

    def summarize(self) -> dict[str, Any]:
        """Summarize the knowledge graph."""
        return self._client.summarize(self._agent_id)

    def deduplicate(self) -> dict[str, Any]:
        """Deduplicate entities in the graph."""
        return self._client.deduplicate(self._agent_id)
