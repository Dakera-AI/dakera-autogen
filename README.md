# autogen-dakera

[![CI](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![dakera.ai](https://img.shields.io/badge/dakera.ai-website-22c55e?style=flat-square)](https://dakera.ai)
[![Docs](https://img.shields.io/badge/docs-dakera.ai%2Fdocs-3b82f6?style=flat-square)](https://dakera.ai/docs)

**Persistent, semantically recalled memory for [AutoGen](https://microsoft.github.io/autogen/) agents, powered by [Dakera](https://dakera.ai).**

Your AutoGen agents remember across runs, processes and restarts. Dakera embeds, stores and
ranks memories server-side, so no embedding model or vector database runs in your process.

---

## Quick Start

### Step 1 — Run Dakera

Dakera is a self-hosted memory server. Start it with Docker:

```bash
docker run -d \
  --name dakera \
  -p 3000:3000 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3

curl http://localhost:3000/health
```

For persistent storage, use the Docker Compose setup:

```bash
curl -sSfL https://raw.githubusercontent.com/Dakera-AI/dakera-deploy/main/docker/docker-compose.yml \
  -o docker-compose.yml
DAKERA_ROOT_API_KEY=dk-mykey docker compose up -d
```

> Full deployment guide (Docker Compose, Kubernetes, Helm): [github.com/Dakera-AI/dakera-deploy](https://github.com/Dakera-AI/dakera-deploy)

### Step 2 — Install the integration

```bash
pip install "autogen-dakera[autogen]" "autogen-ext[openai]"
```

### Step 3 — Give your agent a memory

`DakeraAutoGenMemory` implements AutoGen's
[`Memory`](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html)
interface. Before every model call the agent recalls the memories most relevant to the
conversation and adds them to the model context.

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_dakera import DakeraAutoGenMemory


async def main() -> None:
    memory = DakeraAutoGenMemory(
        api_url="http://localhost:3000",
        api_key="dk-mykey",
        agent_id="my-agent",
    )

    # Teach the agent something; it is stored on the Dakera server.
    await memory.add(
        MemoryContent(content="The user prefers metric units", mime_type=MemoryMimeType.TEXT)
    )

    agent = AssistantAgent(
        name="assistant",
        model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),
        memory=[memory],
    )
    result = await agent.run(task="What will the weather be like in Berlin tomorrow?")
    print(result.messages[-1].content)

    await memory.close()


asyncio.run(main())
```

A new agent, process or machine that uses the same `agent_id` recalls the same memories.

---

## Installation

```bash
# The AutoGen Memory (DakeraAutoGenMemory) and the synchronous helpers
pip install "autogen-dakera[autogen]"

# Only the synchronous helpers (DakeraMemory, sessions, knowledge graph, ...)
pip install autogen-dakera
```

**Requirements:** Python ≥ 3.10, a running Dakera server (see Step 1). The `autogen` extra
installs `autogen-core` / `autogen-agentchat` ≥ 0.4.3 and the async `dakera` client.

**Compatibility:** Tested against Dakera server v0.12.3; works with v0.12.0 – v0.12.2
(dakera Python SDK ≥ 0.14.1). `event_time` needs server v0.12.3;
`DakeraSessionManager.touch()` and `idle_timeout_secs` need v0.12.2.

---

## What's in the package

| Class | Use it for |
|-------|-----------|
| `DakeraAutoGenMemory` | The memory of an AutoGen agent: `AssistantAgent(memory=[...])` (async, AutoGen `Memory`) |
| `DakeraMemory` | Synchronous store / recall / search / forget, for tools and scripts |
| `DakeraSessionManager` | Group memories into conversation sessions |
| `DakeraKnowledgeGraph` | Link memories, query the graph, find paths, summarize |
| `DakeraEntityExtractor` | Named-entity extraction and its per-agent configuration |
| `DakeraNamespaceManager` | Create and configure Dakera namespaces |

---

## `DakeraAutoGenMemory`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_url` | `str` | — | Dakera server URL, e.g. `http://localhost:3000` |
| `agent_id` | `str` | — | The Dakera agent whose memories are read and written |
| `api_key` | `str \| None` | `$DAKERA_API_KEY` | API key (the server's `DAKERA_ROOT_API_KEY` or a key created from it) |
| `recall_k` | `int` | `5` | Memories recalled per query |
| `min_importance` | `float \| None` | `None` | Only recall memories at least this important |
| `importance` | `float \| None` | server default | Importance of added memories |
| `memory_type` | `str` | `"episodic"` | Memory type of added memories |
| `timeout` | `float` | `30.0` | Per-request timeout in seconds |

The AutoGen `Memory` methods:

- **`await add(content, *, importance=None, memory_type=None, tags=None, session_id=None, event_time=None)`**
  stores a `MemoryContent`. Text, Markdown and JSON are stored (a `dict` as JSON, returned as
  a `dict` again); images and binary content raise `ValueError`. `content.metadata` is kept.
  `event_time` is when the remembered event happened (Unix seconds, an RFC 3339 string or a
  timezone-aware `datetime`): recency and time filters use it instead of the time of storage.
- **`await query(query, *, top_k=None, min_importance=None, memory_type=None, tags=None)`**
  returns a `MemoryQueryResult` of at most `top_k` memories, most relevant first. Each result's
  metadata carries the Dakera `id`, `score` (the server's ranking score) and `importance`.
- **`await update_context(model_context)`** — called by the agent before each model call —
  recalls with the last message as the query and adds the results as one system message.
- **`await clear()`** deletes **every memory of the agent** on the server (it cannot be undone).
- **`await close()`** closes the HTTP connections; the memories stay on the server.

`DakeraAutoGenMemory` is an AutoGen component, so `agent.dump_component()` and
`AssistantAgent.load_component(...)` round-trip it. The API key is never written to the
component config; a loaded memory reads it from `DAKERA_API_KEY`.

### Multi-agent team with shared memory

Agents given the same memory (or the same `agent_id`) share what is stored in it:

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_dakera import DakeraAutoGenMemory


async def main() -> None:
    shared_memory = DakeraAutoGenMemory(
        api_url="http://localhost:3000",
        api_key="dk-mykey",
        agent_id="research-team",
        recall_k=8,
    )
    await shared_memory.add(
        MemoryContent(
            content="Finding: retrieval-augmented agents forget less across long tasks",
            mime_type=MemoryMimeType.TEXT,
            metadata={"source": "literature review"},
        )
    )

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    researcher = AssistantAgent(
        name="researcher",
        model_client=model_client,
        memory=[shared_memory],
        system_message="You are a research expert. Build on known findings.",
    )
    analyst = AssistantAgent(
        name="analyst",
        model_client=model_client,
        memory=[shared_memory],
        system_message="You are a data analyst. Build on what the researcher found.",
    )
    team = RoundRobinGroupChat(
        [researcher, analyst],
        termination_condition=MaxMessageTermination(max_messages=4),
    )

    result = await team.run(task="What do we know about memory in AI agents?")
    print(result.messages[-1].content)

    await shared_memory.close()


asyncio.run(main())
```

### Filtering recall

```python
from autogen_dakera import DakeraAutoGenMemory

memory = DakeraAutoGenMemory(
    api_url="http://localhost:3000",
    api_key="dk-mykey",
    agent_id="my-agent",
    min_importance=0.7,  # only surface important memories
    recall_k=3,
)

# Per query: tags match memories carrying at least one of them.
result = await memory.query("travel plans", top_k=5, tags=["travel"])
```

---

## `DakeraMemory` (synchronous)

For tools, scripts and background jobs that work with an agent's memories directly:

```python
from autogen_dakera import DakeraMemory

memory = DakeraMemory(
    api_url="http://localhost:3000",
    api_key="dk-mykey",
    agent_id="my-agent",
    recall_k=5,  # default number of recalled memories
    min_importance=0.0,  # default minimum importance of recalled memories
    importance=0.7,  # default importance of stored memories
)

stored = memory.add(
    "User moved to Berlin",
    tags=["profile"],
    event_time="2021-06-01T00:00:00Z",  # when it happened (server v0.12.3+)
)
for r in memory.query("Where does the user live?", tags=["profile"]):
    print(f"[{r['score']:.3f}] {r['content']}")  # score: the server's ranking score

memory.hybrid_search("Berlin", top_k=3)  # vector + BM25
memory.batch_query(["Berlin", "tea"], top_k=2)
memory.update_importance(stored["id"], 0.9)
merged = memory.consolidate([memory.add("Likes tea")["id"], memory.add("Drinks green tea")["id"]])
memory.forget(stored["id"])
memory.batch_forget([merged["consolidated_memory"]["id"]])
```

`query()` and `batch_query()` return at most `top_k` ranked memories, most relevant first.

## Sessions

```python
from autogen_dakera import DakeraMemory, DakeraSessionManager

memory = DakeraMemory(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")
sessions = DakeraSessionManager(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent"
)

with sessions:  # starts a session, ends it on exit
    memory.add("User asked about password reset", session_id=sessions.active_session_id)
    sessions.touch()  # record activity on a long-running session
    print(sessions.memories(sessions.active_session_id))
```

The server ends a session after 4 h without activity by default (server v0.12.2+;
`get()` then reports `ended_reason: "idle"`). `start(idle_timeout_secs=...)` sets a session's
own timeout (`0` = never) and `touch()` keeps it open.

## Knowledge graph, entities, namespaces

```python
from autogen_dakera import DakeraEntityExtractor, DakeraKnowledgeGraph, DakeraMemory

memory = DakeraMemory(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")
kg = DakeraKnowledgeGraph(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")

a = memory.add("Anna leads the platform team in Berlin")["id"]
b = memory.add("The platform team ships every Friday")["id"]
kg.link(a, b, label="team")
print(kg.find_path(a, b)["hop_count"])
print(kg.summarize([a, b])["summary_memory"]["content"])  # stores a summary memory

entities = DakeraEntityExtractor(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent"
)
entities.configure(["person", "location"])  # extraction for this agent's memories
print(entities.extract("Anna lives in Berlin"))
```

See [`examples/`](examples/) for complete, runnable scripts.

---

## Examples

| Script | Shows |
|--------|-------|
| [`assistant_agent.py`](examples/assistant_agent.py) | An `AssistantAgent` with `DakeraAutoGenMemory` (runs without a model key) |
| [`basic_memory.py`](examples/basic_memory.py) | Store and recall with `DakeraMemory` |
| [`advanced_memory.py`](examples/advanced_memory.py) | Importance, tag filters, event time, consolidation |
| [`batch_operations.py`](examples/batch_operations.py) | Batch recall and forget |
| [`conversation_history.py`](examples/conversation_history.py) | Conversation turns as long-term memory |
| [`hybrid_search.py`](examples/hybrid_search.py) | Semantic recall vs. vector + BM25 search |
| [`knowledge_graph.py`](examples/knowledge_graph.py) | Links, graph queries, paths, summaries |
| [`sessions.py`](examples/sessions.py) | Sessions, idle timeout and `touch()` |

```bash
export DAKERA_API_URL=http://localhost:3000
export DAKERA_API_KEY=dk-mykey
python examples/assistant_agent.py
```

---

## Related packages

| Package | Framework | Language |
|---------|-----------|----------|
| [`crewai-dakera`](https://github.com/Dakera-AI/dakera-crewai) | CrewAI | Python |
| [`langchain-dakera`](https://github.com/Dakera-AI/dakera-langchain) | LangChain | Python |
| [`llamaindex-dakera`](https://github.com/Dakera-AI/dakera-llamaindex) | LlamaIndex | Python |
| [`strands-dakera`](https://github.com/Dakera-AI/strands-dakera) | Strands Agents | Python |
| [`@dakera-ai/langchain`](https://github.com/Dakera-AI/dakera-langchain-js) | LangChain.js | TypeScript |
| [`@dakera-ai/ai-sdk`](https://github.com/Dakera-AI/dakera-ai-sdk) | Vercel AI SDK | TypeScript |

---

## Links

- [Dakera deployment](https://github.com/Dakera-AI/dakera-deploy) — self-hosting the memory server
- [Dakera Python SDK](https://github.com/Dakera-AI/dakera-py) — the API client this package uses
- [Integration guide](https://dakera.ai/integrations/autogen.html) — full setup walkthrough
- [All integrations](https://dakera.ai/integrations/)
- [Changelog](CHANGELOG.md)

---

## License

MIT © [Dakera AI](https://dakera.ai)

---

<div align="center">

**[dakera.ai](https://dakera.ai)** · [Documentation](https://dakera.ai/docs) · [Request Early Access](https://dakera.ai#cta)

</div>
