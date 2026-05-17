"""DakeraEntityExtractor — named entity extraction for AutoGen agents."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient


class DakeraEntityExtractor:
    """Extract named entities from text for AutoGen workflows."""

    def __init__(self, api_url: str, agent_id: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)
        self._agent_id = agent_id

    def extract(self, text: str, entity_types: list[str] | None = None) -> list[dict[str, Any]]:
        """Extract entities from text."""
        result = self._client.extract_entities(text, entity_types=entity_types)
        return [
            {"type": e.entity_type, "value": e.value, "score": e.score}
            for e in result.entities
        ]

    def memory_entities(self, memory_id: str) -> list[dict[str, Any]]:
        """Get entities linked to a memory."""
        result = self._client.memory_entities(memory_id)
        return [
            {"type": e.entity_type, "value": e.value, "score": e.score}
            for e in result.entities
        ]

    def configure(self, entity_types: list[str] | None = None, **kwargs: Any) -> None:
        """Configure entity extraction settings."""
        self._client.configure_namespace_ner(self._agent_id, entity_types=entity_types, **kwargs)
