"""Tests for DakeraNamespaceManager (AutoGen integration)."""

from unittest.mock import MagicMock, patch

import pytest

from autogen_dakera.namespaces import DakeraNamespaceManager


@pytest.fixture
def ns_mgr():
    with patch("autogen_dakera.namespaces.DakeraClient") as MC:
        mock_client = MagicMock()
        MC.return_value = mock_client
        mgr = DakeraNamespaceManager(api_url="http://localhost:3000", api_key="test")
        mgr._client = mock_client
        yield mgr, mock_client


def test_create_namespace(ns_mgr):
    mgr, mock_client = ns_mgr
    mock_ns = MagicMock()
    mock_ns.name = "test-ns"
    mock_ns.dimensions = 384
    mock_ns.index_type = "hnsw"
    mock_ns.vector_count = 0
    mock_client.create_namespace.return_value = mock_ns

    result = mgr.create("test-ns", dimensions=384, index_type="hnsw")
    assert result == {"name": "test-ns", "dimensions": 384, "index_type": "hnsw", "vector_count": 0}


def test_create_with_metadata(ns_mgr):
    mgr, mock_client = ns_mgr
    mock_ns = MagicMock()
    mock_ns.name = "ns2"
    mock_ns.dimensions = None
    mock_ns.index_type = "flat"
    mock_ns.vector_count = 0
    mock_client.create_namespace.return_value = mock_ns

    mgr.create("ns2", metadata={"env": "prod"})
    mock_client.create_namespace.assert_called_once_with(
        "ns2", dimensions=None, index_type=None, metadata={"env": "prod"}
    )


def test_get_namespace(ns_mgr):
    mgr, mock_client = ns_mgr
    mock_ns = MagicMock()
    mock_ns.name = "my-ns"
    mock_ns.dimensions = 768
    mock_ns.index_type = "hnsw"
    mock_ns.vector_count = 1500
    mock_client.get_namespace.return_value = mock_ns

    result = mgr.get("my-ns")
    assert result["name"] == "my-ns"
    assert result["dimensions"] == 768
    assert result["vector_count"] == 1500


def test_list_namespaces(ns_mgr):
    mgr, mock_client = ns_mgr
    ns1 = MagicMock()
    ns1.name = "ns-a"
    ns1.dimensions = 384
    ns1.vector_count = 100
    ns2 = MagicMock()
    ns2.name = "ns-b"
    ns2.dimensions = 768
    ns2.vector_count = 200
    mock_client.list_namespaces.return_value = [ns1, ns2]

    result = mgr.list()
    assert len(result) == 2
    assert result[0] == {"name": "ns-a", "dimensions": 384, "vector_count": 100}


def test_configure_namespace(ns_mgr):
    mgr, mock_client = ns_mgr
    mgr.configure("my-ns", distance="cosine")
    mock_client.configure_namespace.assert_called_once_with("my-ns", distance="cosine")


def test_delete_namespace(ns_mgr):
    mgr, mock_client = ns_mgr
    mgr.delete("old-ns")
    mock_client.delete_namespace.assert_called_once_with("old-ns")


def test_stats(ns_mgr):
    mgr, mock_client = ns_mgr
    mock_stats = MagicMock()
    mock_stats.total_vectors = 5000
    mock_stats.dimensions = 384
    mock_stats.index_type = "hnsw"
    mock_client.get_index_stats.return_value = mock_stats

    result = mgr.stats("my-ns")
    assert result == {"total_vectors": 5000, "dimensions": 384, "index_type": "hnsw"}
