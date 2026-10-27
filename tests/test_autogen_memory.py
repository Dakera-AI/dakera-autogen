"""Tests for DakeraAutoGenMemory (the autogen_core.memory.Memory implementation)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import create_autospec, patch

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import SystemMessage, UserMessage
from autogen_ext.models.replay import ReplayChatCompletionClient
from dakera import AsyncDakeraClient, NotFoundError
from dakera.models import BatchForgetRequest, BatchMemoryFilter, RecallResponse

from autogen_dakera import DakeraAutoGenMemory, DakeraAutoGenMemoryConfig


@pytest.fixture
def client():
    with patch("autogen_dakera.autogen_memory.AsyncDakeraClient") as MockClient:
        mock_client = create_autospec(AsyncDakeraClient, instance=True)
        MockClient.return_value = mock_client
        yield mock_client


@pytest.fixture
def memory(client):
    return DakeraAutoGenMemory(api_url="http://localhost:3300", agent_id="agent-1", recall_k=2)


def _recall(*memories):
    return RecallResponse.from_dict({"memories": list(memories)})


def _mem(mid, content, score, metadata=None, **extra):
    return {
        "id": mid,
        "content": content,
        "importance": 0.7,
        "rank_score": score,
        "metadata": metadata,
        **extra,
    }


def test_is_an_autogen_memory(memory):
    assert isinstance(memory, Memory)


async def test_add_stores_text_with_mime_type(memory, client):
    await memory.add(
        MemoryContent(content="User likes tea", mime_type=MemoryMimeType.TEXT, metadata={"k": 1})
    )
    client.store_memory.assert_awaited_once_with(
        "agent-1",
        "User likes tea",
        memory_type="episodic",
        importance=None,
        metadata={"k": 1, "mime_type": "text/plain"},
        session_id=None,
        tags=None,
        event_time=None,
    )


async def test_add_passes_memory_fields(client):
    memory = DakeraAutoGenMemory(
        api_url="http://x", agent_id="a", importance=0.4, memory_type="semantic"
    )
    await memory.add(
        MemoryContent(content="# Notes", mime_type=MemoryMimeType.MARKDOWN),
        tags=["notes"],
        session_id="urn:chat:42",
        event_time="2024-03-01T10:00:00Z",
    )
    client.store_memory.assert_awaited_once_with(
        "a",
        "# Notes",
        memory_type="semantic",
        importance=0.4,
        metadata={"mime_type": "text/markdown"},
        session_id="urn:chat:42",
        tags=["notes"],
        event_time="2024-03-01T10:00:00Z",
    )
    client.store_memory.reset_mock()
    await memory.add(MemoryContent(content="x", mime_type="text/plain"), importance=0.9)
    assert client.store_memory.await_args.kwargs["importance"] == 0.9


async def test_add_stores_json_as_text(memory, client):
    await memory.add(MemoryContent(content={"city": "Lyon"}, mime_type=MemoryMimeType.JSON))
    args = client.store_memory.await_args
    assert args.args == ("agent-1", '{"city": "Lyon"}')
    assert args.kwargs["metadata"] == {"mime_type": "application/json"}


@pytest.mark.parametrize(
    "content",
    [
        MemoryContent(content=b"\x00\x01", mime_type=MemoryMimeType.BINARY),
        MemoryContent(content="not an image", mime_type=MemoryMimeType.IMAGE),
    ],
)
async def test_add_refuses_non_text(memory, client, content):
    with pytest.raises(ValueError, match="Dakera stores text memories"):
        await memory.add(content)
    client.store_memory.assert_not_awaited()


async def test_query_returns_ranked_memories(memory, client):
    client.recall.return_value = RecallResponse.from_dict(
        {
            "memories": [
                _mem("m-1", "User likes tea", 0.9, {"mime_type": "text/plain", "k": 1}),
                _mem("m-2", '{"city": "Lyon"}', 0.5, {"mime_type": "application/json"}),
                _mem("m-3", "Inline neighbourhood", 0.2, retrieval="neighborhood"),
            ]
        }
    )
    result = await memory.query("What does the user drink?")
    assert [r.content for r in result.results] == ["User likes tea", {"city": "Lyon"}]
    assert result.results[0].mime_type == "text/plain"
    assert result.results[0].metadata == {"k": 1, "id": "m-1", "score": 0.9, "importance": 0.7}
    assert result.results[1].mime_type == "application/json"
    client.recall.assert_awaited_once_with(
        "agent-1",
        "What does the user drink?",
        top_k=2,
        min_importance=None,
        memory_type=None,
        tags=None,
        neighborhood_mode="separate",
    )


async def test_query_caps_at_top_k(memory, client):
    client.recall.return_value = _recall(
        *(_mem(f"m-{i}", f"fact {i}", 1 - i / 10) for i in range(4))
    )
    result = await memory.query("facts")
    assert [r.metadata["id"] for r in result.results] == ["m-0", "m-1"]


async def test_query_options(memory, client):
    client.recall.return_value = _recall()
    query = MemoryContent(content="tea", mime_type=MemoryMimeType.TEXT)
    await memory.query(query, top_k=7, min_importance=0.5, memory_type="semantic", tags=["t"])
    client.recall.assert_awaited_once_with(
        "agent-1",
        "tea",
        top_k=7,
        min_importance=0.5,
        memory_type="semantic",
        tags=["t"],
        neighborhood_mode="separate",
    )
    with pytest.raises(TypeError, match="unexpected query arguments"):
        await memory.query("tea", limit=3)


async def test_query_untagged_memory_is_text(memory, client):
    client.recall.return_value = _recall(_mem("m-1", "stored elsewhere", 0.8))
    result = await memory.query("stored")
    assert result.results[0].mime_type == "text/plain"
    assert result.results[0].metadata == {"id": "m-1", "score": 0.8, "importance": 0.7}


async def test_empty_query_skips_the_server(memory, client):
    assert (await memory.query("  ")).results == []
    client.recall.assert_not_awaited()


async def test_query_of_unknown_agent_on_older_server_is_empty(memory, client):
    client.recall.side_effect = NotFoundError("Namespace not found")
    assert (await memory.query("anything")).results == []


async def test_update_context_adds_one_system_message(memory, client):
    client.recall.return_value = _recall(
        _mem("m-1", "User likes tea", 0.9),
        _mem("m-2", '{"city": "Lyon"}', 0.5, {"mime_type": "application/json"}),
    )
    context = BufferedChatCompletionContext(buffer_size=10)
    await context.add_message(UserMessage(content="What should I drink?", source="user"))
    result = await memory.update_context(context)
    messages = await context.get_messages()
    assert len(messages) == 2
    assert isinstance(messages[1], SystemMessage)
    assert messages[1].content == '\nRelevant memories:\n1. User likes tea\n2. {"city": "Lyon"}'
    assert len(result.memories.results) == 2
    assert client.recall.await_args.args == ("agent-1", "What should I drink?")


async def test_update_context_without_recall_adds_nothing(memory, client):
    client.recall.return_value = _recall()
    context = BufferedChatCompletionContext(buffer_size=10)
    await context.add_message(UserMessage(content="Hello", source="user"))
    result = await memory.update_context(context)
    assert len(await context.get_messages()) == 1
    assert result.memories.results == []


async def test_update_context_of_empty_context(memory, client):
    result = await memory.update_context(BufferedChatCompletionContext(buffer_size=10))
    assert result.memories.results == []
    client.recall.assert_not_awaited()


async def test_update_context_queries_text_parts_of_multimodal_message(memory, client):
    client.recall.return_value = _recall()
    context = BufferedChatCompletionContext(buffer_size=10)
    await context.add_message(UserMessage(content=["first part", "second part"], source="user"))
    await memory.update_context(context)
    assert client.recall.await_args.args == ("agent-1", "first part\nsecond part")


async def test_clear_forgets_every_memory_of_the_agent(memory, client):
    await memory.clear()
    client.batch_forget.assert_awaited_once_with(
        BatchForgetRequest(agent_id="agent-1", filter=BatchMemoryFilter(min_importance=0.0))
    )


async def test_clear_of_unknown_agent_on_older_server(memory, client):
    client.batch_forget.side_effect = NotFoundError("Namespace not found")
    await memory.clear()


async def test_close_closes_the_client(memory, client):
    await memory.close()
    client.close.assert_awaited_once_with()


async def test_cancellation_token_cancels_the_request(memory, client):
    started = asyncio.Event()

    async def slow_recall(*args, **kwargs):
        started.set()
        await asyncio.sleep(10)

    client.recall.side_effect = slow_recall
    token = CancellationToken()
    task = asyncio.create_task(memory.query("anything", cancellation_token=token))
    await started.wait()
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_component_round_trip(client, monkeypatch):
    monkeypatch.delenv("DAKERA_API_KEY", raising=False)
    memory = DakeraAutoGenMemory(
        api_url="http://localhost:3300", agent_id="agent-1", api_key="dk-secret", recall_k=3
    )
    model = memory.dump_component()
    assert model.provider == "autogen_dakera.DakeraAutoGenMemory"
    assert "api_key" not in model.config
    assert "dk-secret" not in model.model_dump_json()

    monkeypatch.setenv("DAKERA_API_KEY", "dk-from-env")
    loaded = DakeraAutoGenMemory.load_component(json.loads(model.model_dump_json()))
    assert isinstance(loaded, DakeraAutoGenMemory)
    assert loaded.agent_id == "agent-1"
    assert loaded._to_config() == DakeraAutoGenMemoryConfig(
        api_url="http://localhost:3300", agent_id="agent-1", api_key="dk-from-env", recall_k=3
    )


def test_api_key_defaults_to_environment(monkeypatch):
    monkeypatch.setenv("DAKERA_API_KEY", "dk-env")
    with patch("autogen_dakera.autogen_memory.AsyncDakeraClient") as MockClient:
        DakeraAutoGenMemory(api_url="http://x", agent_id="a")
        DakeraAutoGenMemory(api_url="http://x", agent_id="a", api_key="dk-explicit")
    assert [c.kwargs["api_key"] for c in MockClient.call_args_list] == ["dk-env", "dk-explicit"]


async def test_assistant_agent_sees_recalled_memories(memory, client):
    client.recall.return_value = _recall(_mem("m-1", "The user prefers metric units", 0.9))
    model_client = ReplayChatCompletionClient(["It is 20 degrees Celsius."])
    agent = AssistantAgent("assistant", model_client=model_client, memory=[memory])

    result = await agent.run(task="What is the weather?")

    assert result.messages[-1].content == "It is 20 degrees Celsius."
    sent = [m.content for m in model_client.create_calls[0]["messages"]]
    assert "\nRelevant memories:\n1. The user prefers metric units" in sent
    assert client.recall.await_args.args == ("agent-1", "What is the weather?")
