"""Tests for DakeraMemory (AutoGen integration)."""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from dakera import DakeraClient

from autogen_dakera import DakeraMemory


@pytest.fixture
def memory():
    with patch("autogen_dakera.memory.DakeraClient") as MockClient:
        mock_client = create_autospec(DakeraClient, instance=True)
        MockClient.return_value = mock_client
        m = DakeraMemory(
            api_url="http://localhost:3000", api_key="test-key", agent_id="agent-1", recall_k=3
        )
        m._client = mock_client
        yield m, mock_client


def test_add_stores_memory(memory):
    m, mock_client = memory
    m.add("Project deadline is April 15")
    mock_client.store_memory.assert_called_once_with(
        "agent-1", content="Project deadline is April 15", memory_type="episodic", importance=0.7
    )


def _recall(*memories, **extra):
    from dakera.models import RecallResponse

    return RecallResponse.from_dict({"memories": list(memories), **extra})


def _mem(mid, content, score, **extra):
    return {"id": mid, "content": content, "importance": 0.7, "rank_score": score, **extra}


def test_query_returns_memories(memory):
    m, mock_client = memory
    mock_client.recall.return_value = _recall(_mem("m-1", "Project deadline is April 15", 0.9))
    results = m.query("What is the deadline?")
    assert results == [
        {
            "content": "Project deadline is April 15",
            "id": "m-1",
            "score": 0.9,
            "importance": 0.7,
            "metadata": None,
        }
    ]
    mock_client.recall.assert_called_once_with(
        "agent-1", query="What is the deadline?", top_k=3, neighborhood_mode="separate"
    )


def test_query_wraps_non_dict_results(memory):
    m, mock_client = memory
    mem = MagicMock(content="plain string", id="m-2", score=0.8, metadata=None)
    mock_recall = MagicMock()
    mock_recall.ranked = [mem]
    mock_client.recall.return_value = mock_recall
    results = m.query("test")
    assert results[0]["content"] == "plain string"


def test_query_leaves_out_inline_neighborhood_context(memory):
    # A server that appends neighbourhood context inline (v0.12.3 default)
    # must not push the result past top_k.
    m, mock_client = memory
    mock_client.recall.return_value = _recall(
        _mem("m-1", "a", 0.9),
        _mem("m-2", "b", 0.8),
        _mem("n-1", "context", 0.99, retrieval="neighborhood"),
        _mem("m-3", "c", 0.7),
        _mem("m-4", "d", 0.6),
    )
    results = m.query("q")
    assert [r["id"] for r in results] == ["m-1", "m-2", "m-3"]


def test_query_scores_by_rank_score(memory):
    m, mock_client = memory
    mock_client.recall.return_value = _recall(
        {"id": "m-1", "content": "a", "rank_score": 0.42, "smart_score": 0.9, "score": 0.1}
    )
    assert m.query("q")[0]["score"] == 0.42


def test_batch_query_caps_each_result_at_top_k(memory):
    m, mock_client = memory
    mock_client.recall.return_value = _recall(
        _mem("m-1", "a", 0.9),
        _mem("n-1", "ctx", 0.5, retrieval="neighborhood"),
        _mem("m-2", "b", 0.8),
    )
    results = m.batch_query(["x", "y"], top_k=1)
    assert results == [[{"content": "a", "id": "m-1", "score": 0.9}]] * 2
    mock_client.recall.assert_called_with(
        "agent-1", query="y", top_k=1, neighborhood_mode="separate"
    )


def test_add_forwards_event_time(memory):
    m, mock_client = memory
    m.add("Met Anna in Berlin", event_time="2024-03-01T10:00:00Z")
    mock_client.store_memory.assert_called_once_with(
        "agent-1",
        content="Met Anna in Berlin",
        memory_type="episodic",
        importance=0.7,
        event_time="2024-03-01T10:00:00Z",
    )


def test_consolidate_without_ids(memory):
    m, mock_client = memory
    m.consolidate()
    mock_client.consolidate.assert_called_once_with("agent-1")


def test_consolidate_with_ids(memory):
    m, mock_client = memory
    m.consolidate(["m-1", "m-2"])
    mock_client.consolidate.assert_called_once_with("agent-1", memory_ids=["m-1", "m-2"])


def test_clear_is_noop(memory):
    m, mock_client = memory
    m.clear()
    mock_client.forget.assert_not_called()


def test_query_forwards_tags(memory):
    # recall() takes tags since dakera 0.13.1 (it raised TypeError before).
    from dakera.models import RecallResponse

    obj, mock_client = memory
    mock_client.recall.return_value = RecallResponse.from_dict({"memories": []})
    assert obj.query("q", tags=["work"]) == []
    _, kwargs = mock_client.recall.call_args
    assert kwargs["tags"] == ["work"]
