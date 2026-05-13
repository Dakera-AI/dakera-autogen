"""Tests for DakeraMemory (AutoGen integration)."""

from unittest.mock import MagicMock, patch

import pytest

from autogen_dakera import DakeraMemory


@pytest.fixture
def memory():
    with patch("autogen_dakera.memory.DakeraClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        m = DakeraMemory(api_url="http://localhost:3000", api_key="test-key",
                         agent_id="agent-1", recall_k=3)
        m._client = mock_client
        yield m, mock_client


def test_add_stores_memory(memory):
    m, mock_client = memory
    m.add("Project deadline is April 15")
    mock_client.store_memory.assert_called_once_with(
        "agent-1", content="Project deadline is April 15",
        memory_type="episodic", importance=0.7, metadata={})


def test_query_returns_memories(memory):
    m, mock_client = memory
    mock_client.recall.return_value = [{"content": "Project deadline is April 15"}]
    results = m.query("What is the deadline?")
    assert len(results) == 1
    mock_client.recall.assert_called_once_with(
        "agent-1", query="What is the deadline?", top_k=3, min_importance=None)


def test_query_wraps_non_dict_results(memory):
    m, mock_client = memory
    mock_client.recall.return_value = ["plain string"]
    results = m.query("test")
    assert results == [{"content": "plain string"}]


def test_clear_is_noop(memory):
    m, mock_client = memory
    m.clear()
    mock_client.forget.assert_not_called()
