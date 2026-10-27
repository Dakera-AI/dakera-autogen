"""Live tests against a real Dakera server.

Skipped unless ``DAKERA_API_URL`` is set (the CI integration job runs them
against the pinned ``ghcr.io/dakera-ai/dakera`` image). Each run uses fresh
agent ids, so the tests do not depend on what the server already holds.
"""

from __future__ import annotations

import os
import uuid

import pytest

from autogen_dakera import (
    DakeraAutoGenMemory,
    DakeraEntityExtractor,
    DakeraKnowledgeGraph,
    DakeraMemory,
    DakeraNamespaceManager,
    DakeraSessionManager,
)

API_URL = os.environ.get("DAKERA_API_URL", "")
API_KEY = os.environ.get("DAKERA_API_KEY", "")

pytestmark = pytest.mark.skipif(not API_URL, reason="DAKERA_API_URL not set")


@pytest.fixture
def agent_id() -> str:
    return f"autogen-it-{uuid.uuid4().hex[:12]}"


def test_memory_round_trip(agent_id: str) -> None:
    memory = DakeraMemory(API_URL, agent_id, api_key=API_KEY, recall_k=2)
    # An agent that has stored nothing recalls nothing; "What do I build?" is a query a
    # server before v0.12.3 answers with 404 NAMESPACE_NOT_FOUND.
    assert memory.query("What do I build?") == []

    stored = [
        memory.add("Project Falcon ships on April 15", tags=["project"]),
        memory.add("Project Falcon is written in Rust", tags=["project"]),
        memory.add("Anna prefers tea over coffee", event_time="2024-03-01T10:00:00Z"),
    ]
    ids = [m["id"] for m in stored]
    assert stored[2]["metadata"]["_dakera_event_time"] == 1709287200

    results = memory.query("When does Project Falcon ship?")
    assert 1 <= len(results) <= 2
    assert results[0]["id"] == ids[0]
    assert set(results[0]) == {"content", "id", "score", "importance", "metadata"}
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    assert {r["id"] for r in memory.query("Falcon", tags=["project"], top_k=5)} <= set(ids[:2])
    assert all(len(batch) <= 1 for batch in memory.batch_query(["Falcon", "tea"], top_k=1))
    assert memory.hybrid_search("Falcon Rust", top_k=2)

    memory.update_importance(ids[2], 0.95)
    assert memory.query("tea", min_importance=0.9)[0]["id"] == ids[2]
    assert memory.stats()["total_memories"] == 3

    merged = memory.consolidate(ids[:2])
    assert sorted(merged["source_memory_ids"]) == sorted(ids[:2])
    memory.forget(ids[2])
    memory.batch_forget([merged["consolidated_memory"]["id"]])


def test_sessions(agent_id: str) -> None:
    sessions = DakeraSessionManager(API_URL, agent_id, api_key=API_KEY)
    memory = DakeraMemory(API_URL, agent_id, api_key=API_KEY)

    with sessions:
        sid = sessions.active_session_id
        assert sid is not None
        assert sessions.touch()["session_state"] == "active"
        stored = memory.add(
            "User asked about password reset. The reset link had expired, so we sent a new one.",
            session_id=sid,
        )
        assert stored["session_state"] == "active"
        # The server also lists the sentences it derives; memories() leaves them out.
        assert [m["id"] for m in sessions.memories(sid)] == [stored["id"]]
        assert sid in [s["id"] for s in sessions.list(active_only=True)]
    assert sessions.active_session_id is None
    assert sessions.get(sid)["ended_reason"] == "client"

    sid = sessions.start(idle_timeout_secs=0)
    sessions.end()
    assert sessions.get(sid)["ended_at"] is not None


def test_knowledge_graph(agent_id: str) -> None:
    memory = DakeraMemory(API_URL, agent_id, api_key=API_KEY)
    kg = DakeraKnowledgeGraph(API_URL, agent_id, api_key=API_KEY)
    a = memory.add("Anna leads the platform team in Berlin")["id"]
    b = memory.add("The platform team ships the Berlin release every Friday")["id"]

    link = kg.link(a, b, label="team")
    assert (link["from_id"], link["to_id"]) == (a, b)
    assert kg.query(root_id=a)["edge_count"] >= 1
    assert kg.find_path(a, b)["hop_count"] >= 1
    assert kg.export()["edge_count"] >= 1
    assert isinstance(kg.build(a, depth=1), dict)
    assert kg.summarize([a, b])["source_count"] == 2
    assert isinstance(kg.deduplicate(), dict)


def test_entities(agent_id: str) -> None:
    memory = DakeraMemory(API_URL, agent_id, api_key=API_KEY)
    entities = DakeraEntityExtractor(API_URL, agent_id, api_key=API_KEY)
    memory.add("first memory creates the agent namespace")
    entities.configure(["person", "location"])
    assert isinstance(entities.extract("Anna lives in Berlin"), list)
    mid = memory.add("Anna moved to Berlin in 2021")["id"]
    assert isinstance(entities.memory_entities(mid), list)


def test_namespaces() -> None:
    namespaces = DakeraNamespaceManager(API_URL, api_key=API_KEY)
    name = f"autogen-it-ns-{uuid.uuid4().hex[:12]}"
    created = namespaces.create(name, dimensions=8)
    assert created["name"] == name
    try:
        assert namespaces.get(name)["dimensions"] == 8
        assert name in [ns["name"] for ns in namespaces.list()]
        namespaces.configure(name, dimension=8, distance="cosine")
        assert namespaces.stats(name)["dimensions"] == 8
    finally:
        namespaces.delete(name)


async def test_autogen_memory_with_assistant_agent(agent_id: str) -> None:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_core.memory import MemoryContent, MemoryMimeType
    from autogen_ext.models.replay import ReplayChatCompletionClient

    memory = DakeraAutoGenMemory(API_URL, agent_id, api_key=API_KEY or None, recall_k=2)
    try:
        assert (await memory.query("What do I build?")).results == []
        await memory.add(
            MemoryContent(content="The user prefers metric units", mime_type=MemoryMimeType.TEXT)
        )
        await memory.add(
            MemoryContent(content={"home": "Lyon"}, mime_type=MemoryMimeType.JSON),
            event_time="2024-03-01T10:00:00Z",
        )
        await memory.add(MemoryContent(content="Paris is in France", mime_type="text/plain"))

        result = await memory.query("Which units does the user prefer?")
        assert 1 <= len(result.results) <= 2
        assert result.results[0].content == "The user prefers metric units"
        assert set(result.results[0].metadata or {}) >= {"id", "score", "importance"}
        homes = [r for r in (await memory.query("Where is home?", top_k=3)).results]
        assert {"home": "Lyon"} in [r.content for r in homes]

        model_client = ReplayChatCompletionClient(["It is 20 degrees Celsius."])
        agent = AssistantAgent("assistant", model_client=model_client, memory=[memory])
        await agent.run(task="What is the weather? Use my preferred units.")
        sent = [str(m.content) for m in model_client.create_calls[0]["messages"]]
        assert any("1. The user prefers metric units" in m for m in sent)

        await memory.clear()
        assert (await memory.query("units")).results == []
    finally:
        await memory.close()
