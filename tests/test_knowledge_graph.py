"""Tests for DakeraKnowledgeGraph (AutoGen integration)."""

from unittest.mock import MagicMock, patch

import pytest

from autogen_dakera.knowledge_graph import DakeraKnowledgeGraph


@pytest.fixture
def kg():
    with patch("autogen_dakera.knowledge_graph.DakeraClient") as MC:
        mock_client = MagicMock()
        MC.return_value = mock_client
        graph = DakeraKnowledgeGraph(
            api_url="http://localhost:3000", agent_id="test-agent", api_key="test"
        )
        graph._client = mock_client
        yield graph, mock_client


def test_query_returns_edges(kg):
    graph, mock_client = kg
    mock_edge = MagicMock()
    mock_edge.source_id = "a"
    mock_edge.target_id = "b"
    mock_edge.edge_type = "related_to"
    mock_result = MagicMock()
    mock_result.edges = [mock_edge]
    mock_result.node_count = 2
    mock_result.edge_count = 1
    mock_client.knowledge_query.return_value = mock_result

    result = graph.query(root_id="a", max_depth=2)
    assert result["edges"] == [{"source": "a", "target": "b", "type": "related_to"}]
    assert result["node_count"] == 2
    assert result["edge_count"] == 1


def test_query_with_edge_type_filter(kg):
    graph, mock_client = kg
    mock_result = MagicMock()
    mock_result.edges = []
    mock_result.node_count = 0
    mock_result.edge_count = 0
    mock_client.knowledge_query.return_value = mock_result

    graph.query(edge_type="causes", limit=50)
    mock_client.knowledge_query.assert_called_once_with(
        "test-agent", root_id=None, edge_type="causes", max_depth=3, limit=50
    )


def test_find_path(kg):
    graph, mock_client = kg
    mock_result = MagicMock()
    mock_result.path = ["a", "c", "b"]
    mock_result.hop_count = 2
    mock_client.knowledge_path.return_value = mock_result

    result = graph.find_path("a", "b")
    assert result == {"path": ["a", "c", "b"], "hop_count": 2}


def test_link_memories(kg):
    graph, mock_client = kg
    graph.link("mem_1", "mem_2", edge_type="causes")
    mock_client.memory_link.assert_called_once_with("mem_1", "mem_2", edge_type="causes")


def test_link_default_edge_type(kg):
    graph, mock_client = kg
    graph.link("mem_1", "mem_2")
    mock_client.memory_link.assert_called_once_with("mem_1", "mem_2", edge_type="linked_by")


def test_export(kg):
    graph, mock_client = kg
    mock_edge = MagicMock()
    mock_edge.source_id = "x"
    mock_edge.target_id = "y"
    mock_edge.edge_type = "linked_by"
    mock_result = MagicMock()
    mock_result.edges = [mock_edge]
    mock_result.node_count = 5
    mock_result.edge_count = 3
    mock_client.knowledge_export.return_value = mock_result

    result = graph.export()
    assert result["node_count"] == 5
    assert len(result["edges"]) == 1


def test_build(kg):
    graph, mock_client = kg
    mock_client.knowledge_graph.return_value = {"status": "ok"}
    result = graph.build(memory_id="mem_1", depth=2)
    assert result == {"status": "ok"}
    mock_client.knowledge_graph.assert_called_once_with("test-agent", memory_id="mem_1", depth=2)


def test_summarize(kg):
    graph, mock_client = kg
    mock_client.summarize.return_value = {"summary": "3 clusters"}
    result = graph.summarize()
    assert result == {"summary": "3 clusters"}


def test_deduplicate(kg):
    graph, mock_client = kg
    mock_client.deduplicate.return_value = {"merged": 2}
    result = graph.deduplicate()
    assert result == {"merged": 2}
