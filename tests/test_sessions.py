"""Tests for DakeraSessionManager (AutoGen integration)."""

from unittest.mock import MagicMock, patch

import pytest

from autogen_dakera.sessions import DakeraSessionManager


@pytest.fixture
def session_mgr():
    with patch("autogen_dakera.sessions.DakeraClient") as MC:
        mock_client = MagicMock()
        MC.return_value = mock_client
        mgr = DakeraSessionManager(
            api_url="http://localhost:3000", agent_id="test-agent", api_key="test"
        )
        mgr._client = mock_client
        yield mgr, mock_client


def test_start_session_returns_id(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.start_session.return_value = {"id": "sess_123"}
    sid = mgr.start(metadata={"type": "test"})
    assert sid == "sess_123"
    assert mgr.active_session_id == "sess_123"
    mock_client.start_session.assert_called_once_with("test-agent", metadata={"type": "test"})


def test_end_session_clears_active(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.start_session.return_value = {"id": "sess_456"}
    mgr.start()
    mgr.end()
    assert mgr.active_session_id is None
    mock_client.end_session.assert_called_once_with("sess_456")


def test_end_without_active_raises(session_mgr):
    mgr, _ = session_mgr
    with pytest.raises(RuntimeError, match="No active session"):
        mgr.end()


def test_get_session_returns_details(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.get_session.return_value = {
        "id": "sess_789",
        "agent_id": "test-agent",
        "started_at": 1700000000,
        "ended_at": None,
        "metadata": {"k": "v"},
        "memory_count": 5,
    }
    result = mgr.get("sess_789")
    assert result["id"] == "sess_789"
    assert result["memory_count"] == 5
    assert result["metadata"] == {"k": "v"}


def test_list_sessions(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.list_sessions.return_value = [
        {"id": "s1", "started_at": 100, "ended_at": 200, "memory_count": 3},
        {"id": "s2", "started_at": 300, "ended_at": None, "memory_count": 0},
    ]
    result = mgr.list(active_only=True)
    assert len(result) == 2
    assert result[0]["id"] == "s1"
    mock_client.list_sessions.assert_called_once_with("test-agent", active_only=True)


def test_memories_returns_formatted(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.session_memories.return_value = [
        {"id": "m1", "content": "Hello", "importance": 0.8},
        {"id": "m2", "content": "World", "importance": 0.5},
    ]
    result = mgr.memories("sess_123")
    assert len(result) == 2
    assert result[0] == {"id": "m1", "content": "Hello", "importance": 0.8}


def test_context_manager(session_mgr):
    mgr, mock_client = session_mgr
    mock_client.start_session.return_value = {"id": "sess_ctx"}
    with mgr:
        assert mgr.active_session_id == "sess_ctx"
    assert mgr.active_session_id is None
    mock_client.end_session.assert_called_once_with("sess_ctx")
