"""DakeraNamespaceManager — namespace management for AutoGen workflows."""

from __future__ import annotations

from typing import Any

from dakera import DakeraClient
from dakera.models import DistanceMetric


class DakeraNamespaceManager:
    """Manage Dakera namespaces for data isolation in AutoGen."""

    def __init__(self, api_url: str, api_key: str = "") -> None:
        self._client = DakeraClient(api_url, api_key=api_key)

    def create(
        self,
        name: str,
        *,
        dimensions: int | None = None,
        index_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a namespace."""
        ns = self._client.create_namespace(
            name, dimensions=dimensions, index_type=index_type, metadata=metadata
        )
        return {
            "name": ns.name,
            "dimensions": ns.dimensions,
            "index_type": ns.index_type,
            "vector_count": ns.vector_count,
        }

    def get(self, name: str) -> dict[str, Any]:
        """Get namespace details."""
        ns = self._client.get_namespace(name)
        return {
            "name": ns.name,
            "dimensions": ns.dimensions,
            "index_type": ns.index_type,
            "vector_count": ns.vector_count,
        }

    def list(self) -> list[dict[str, Any]]:
        """List all namespaces."""
        namespaces = self._client.list_namespaces()
        return [
            {"name": ns.name, "dimensions": ns.dimensions, "vector_count": ns.vector_count}
            for ns in namespaces
        ]

    def configure(self, name: str, *, dimension: int, distance: str | None = None) -> None:
        """Create or update a namespace's vector configuration.

        ``dimension`` is required by the server; ``distance`` is ``cosine``,
        ``euclidean`` or ``dot_product`` (server default: cosine).
        """
        self._client.configure_namespace(
            name,
            dimension=dimension,
            distance=DistanceMetric(distance) if distance is not None else None,
        )

    def delete(self, name: str) -> None:
        """Delete a namespace."""
        self._client.delete_namespace(name)

    def stats(self, name: str) -> dict[str, Any]:
        """Get namespace statistics."""
        s = self._client.get_index_stats(name)
        return {
            "total_vectors": s.total_vectors,
            "dimensions": s.dimensions,
            "index_type": s.index_type,
        }
