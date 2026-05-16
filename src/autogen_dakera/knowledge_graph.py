"""DakeraKnowledgeGraph — knowledge graph operations for AutoGen agents."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraKnowledgeGraph:
    """Knowledge graph for entity relationships in AutoGen workflows."""

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id

    def query(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Query the knowledge graph."""
        result = self._client.knowledge_query(self._agent_id, query=query, **kwargs)
        return {"nodes": result.nodes, "edges": result.edges}

    def traverse(self, entity_id: str, *, depth: int = 2, direction: str = "both") -> dict[str, Any]:
        """Traverse from an entity node."""
        result = self._client.knowledge_path(
            self._agent_id, source=entity_id, depth=depth, direction=direction
        )
        return {"nodes": result.nodes, "edges": result.edges}

    def link(self, memory_id: str, entity_id: str, relation: str = "relates_to") -> None:
        """Link a memory to an entity."""
        self._client.memory_link(self._agent_id, memory_id=memory_id, entity_id=entity_id, relation=relation)

    def export(self) -> dict[str, Any]:
        """Export the full knowledge graph."""
        result = self._client.knowledge_export(self._agent_id)
        return {"nodes": result.nodes, "edges": result.edges}

    def build(self) -> dict[str, Any]:
        """Build/rebuild the knowledge graph from memories."""
        result = self._client.knowledge_graph(self._agent_id)
        return {"nodes": result.nodes, "edges": result.edges}

    def summarize(self) -> dict[str, Any]:
        """Summarize the knowledge graph."""
        return self._client.summarize(self._agent_id)

    def deduplicate(self) -> dict[str, Any]:
        """Deduplicate entities in the graph."""
        return self._client.deduplicate(self._agent_id)
