# autogen-dakera

**Persistent, decay-weighted memory for [AutoGen](https://microsoft.github.io/autogen/) agents, powered by a self-hosted [Dakera](https://dakera.ai) server.**

[![CI](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Dakera-AI/dakera-autogen/blob/main/LICENSE)
[![Dakera server](https://img.shields.io/badge/Dakera%20server-v0.12.3-D4A843)](https://dakera.ai)
[![LoCoMo](https://img.shields.io/badge/LoCoMo-88.2%25%20Recall%4020-brightgreen)](https://dakera.ai/benchmark)

Give an `AssistantAgent` a memory that outlives the process: `DakeraAutoGenMemory` implements
AutoGen's `Memory` interface, so before every model call the agent recalls what it knows that
is relevant to the conversation. Dakera embeds, stores and ranks the memories on the server —
no embedding API key, no vector database in your process — and ranks them by relevance,
importance and recency.

## Why Dakera

- **Drop-in AutoGen `Memory`** — pass `DakeraAutoGenMemory` to `AssistantAgent(memory=[...])`;
  it serializes as an AutoGen component and honours `CancellationToken`.
- **Memory that survives restarts** — a new agent, process or machine with the same `agent_id`
  recalls the same memories; agents in a team can share one.
- **Decay-weighted recall** — results are ranked by semantic relevance, importance and recency,
  not by vector distance alone; filter by importance, memory type and tags.
- **No embedding model to run or pay for** — the Dakera server embeds text itself.
- **Self-hosted, one container** — your agents' memories stay on your infrastructure.
- **Measured** — 88.2% Recall@20 on the [LoCoMo long-conversation memory benchmark](https://dakera.ai/benchmark).

## Contents

- [Quick start](#quick-start)
- [Compatibility](#compatibility)
- [What's new in 0.4.0](#whats-new-in-040)
- [`DakeraAutoGenMemory`](#dakeraautogenmemory)
- [`DakeraMemory`](#dakeramemory)
- [`DakeraSessionManager`](#dakerasessionmanager)
- [`DakeraKnowledgeGraph`](#dakeraknowledgegraph)
- [`DakeraEntityExtractor`](#dakeraentityextractor)
- [`DakeraNamespaceManager`](#dakeranamespacemanager)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Related packages](#related-packages)
- [Links](#links)
- [License](#license)

## Quick start

**1. Run Dakera**

```bash
docker run -d --name dakera -p 3000:3000 -v dakera-data:/data \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3

curl http://localhost:3000/health   # {"service":"dakera","status":"healthy",...}
```

The image ships its embedding model, so the server is ready in seconds. Docker Compose,
Kubernetes and Helm setups are in [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy).

**2. Install**

```bash
pip install "autogen-dakera[autogen]" "autogen-ext[openai]"
```

**3. Give your agent a memory**

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
        model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),  # needs OPENAI_API_KEY
        memory=[memory],
    )
    result = await agent.run(task="What will the weather be like in Berlin tomorrow?")
    print(result.messages[-1].content)  # the recalled preference was in the model's context

    await memory.close()


asyncio.run(main())
```

Run it again — in a new process, on another machine — and the agent still knows. No OpenAI
key? [`examples/assistant_agent.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/assistant_agent.py)
runs the same agent with a replay model client and prints what the model is sent.

## Compatibility

| autogen-dakera | Dakera server | `dakera` SDK | AutoGen (`autogen` extra) | Python |
|---|---|---|---|---|
| **0.4.x** | v0.12.0 – **v0.12.3** | ≥ 0.14.1 | `autogen-core` / `autogen-agentchat` ≥ 0.4.3 | ≥ 3.10 |
| 0.3.x | v0.12.0 | ≥ 0.13.1 | — | ≥ 3.10 |

`event_time` needs server v0.12.3; sessions' `idle_timeout_secs` and `touch()` need v0.12.2.
Older v0.12 servers ignore the new fields.

## What's new in 0.4.0

- **`DakeraAutoGenMemory`** — a real AutoGen `Memory` for `AssistantAgent(memory=[...])`
  (the README's previous example passed `DakeraMemory`, which is not one).
- Dakera server **v0.12.3** support with `dakera>=0.14.1`; recall returns at most `top_k`
  ranked memories and `score` is the server's ranking score.
- `event_time` — when the remembered event happened, for history written after the fact.
- `consolidate(memory_ids)` merges exactly the memories you name.
- Sessions: `idle_timeout_secs`, `touch()` and `ended_reason` (the server ends idle sessions).
- `DakeraKnowledgeGraph.deduplicate(threshold=, dry_run=)`.

Full list: [CHANGELOG](https://github.com/Dakera-AI/dakera-autogen/blob/main/CHANGELOG.md).

## `DakeraAutoGenMemory`

The memory of an AutoGen agent (async, implements `autogen_core.memory.Memory`).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | — | Dakera server URL, e.g. `http://localhost:3000` |
| `agent_id` | `str` | — | The Dakera agent whose memories are read and written |
| `api_key` | `str \| None` | `$DAKERA_API_KEY` | API key (the server's `DAKERA_ROOT_API_KEY` or a key created with it) |
| `recall_k` | `int` | `5` | Memories recalled per query |
| `min_importance` | `float \| None` | `None` | Only recall memories at least this important |
| `importance` | `float \| None` | server default | Importance (0.0–1.0) of added memories |
| `memory_type` | `str` | `"episodic"` | Memory type of added memories (`episodic`, `semantic`, `procedural`, `working`) |
| `timeout` | `float` | `30.0` | Per-request timeout in seconds |

Methods:

- **`await add(content, *, importance=None, memory_type=None, tags=None, session_id=None, event_time=None)`**
  stores a `MemoryContent`. Text, Markdown and JSON are stored (a `dict` as JSON, returned as
  a `dict` again); images and binary content raise `ValueError`. `content.metadata` is kept.
  `event_time` is when the remembered event happened (Unix seconds, an RFC 3339 string or a
  timezone-aware `datetime`); recency and time filters use it instead of the time of storage.
- **`await query(query, *, top_k=None, min_importance=None, memory_type=None, tags=None)`**
  returns a `MemoryQueryResult` of at most `top_k` memories, most relevant first. Each result's
  metadata carries the Dakera `id`, `score` (the server's ranking score) and `importance`.
  `tags` matches memories carrying at least one of the tags.
- **`await update_context(model_context)`** — called by the agent before each model call —
  recalls with the last message as the query and adds the results as one system message.
- **`await clear()`** deletes **every memory of the agent** on the server. It cannot be undone.
- **`await close()`** closes the HTTP connections; the memories stay on the server.

`DakeraAutoGenMemory` is an AutoGen component: `agent.dump_component()` and
`AssistantAgent.load_component(...)` round-trip it. The API key is never written to the
component config; a loaded memory reads it from `DAKERA_API_KEY`.

### A team that shares what it learns

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

### Filtered recall

```python
import asyncio

from autogen_core.memory import MemoryContent, MemoryMimeType

from autogen_dakera import DakeraAutoGenMemory


async def main() -> None:
    memory = DakeraAutoGenMemory(
        api_url="http://localhost:3000",
        api_key="dk-mykey",
        agent_id="my-agent",
        min_importance=0.7,  # only surface important memories
        recall_k=3,
    )
    await memory.add(
        MemoryContent(content="Flight to Lisbon on May 3", mime_type=MemoryMimeType.TEXT),
        importance=0.9,
        tags=["travel"],
        event_time="2026-05-03T08:00:00Z",  # when it happens (server v0.12.3+)
    )

    # Per query: tags match memories carrying at least one of them.
    result = await memory.query("travel plans", top_k=5, tags=["travel"])
    for item in result.results:
        print(item.metadata["score"], item.content)

    await memory.close()


asyncio.run(main())
```

## `DakeraMemory`

Synchronous store / recall / search / forget of an agent's memories, for tools, scripts and
background jobs.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | — | Dakera server URL |
| `agent_id` | `str` | — | The agent whose memories are read and written |
| `api_key` | `str` | `""` | API key |
| `recall_k` | `int` | `5` | Memories returned by `query()` by default |
| `min_importance` | `float` | `0.0` | Default minimum importance of recalled memories (`0.0` = no filter) |
| `importance` | `float` | `0.7` | Default importance of stored memories |

```python
from autogen_dakera import DakeraMemory

memory = DakeraMemory(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")

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
print(memory.stats())
```

- `add(content, metadata=None, *, memory_type="episodic", importance=None, tags=None, ttl_seconds=None, session_id=None, event_time=None)`
- `query(query, top_k=None, *, tags=None, memory_type=None, min_importance=None)` and
  `batch_query(queries, top_k=None)` return at most `top_k` ranked memories, most relevant
  first, as dicts with `content`, `id`, `score`, `importance` and `metadata`.
- `consolidate(memory_ids)` merges at least two memories into one; `clear()` deletes every
  memory of the agent.

## `DakeraSessionManager`

Groups an agent's memories into conversation sessions. Use it as a context manager to start a
session and end it on exit.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | — | Dakera server URL |
| `agent_id` | `str` | — | The agent the sessions belong to |
| `api_key` | `str` | `""` | API key |

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

The server ends a session after 4 h without activity by default (server v0.12.2+; `get()` then
reports `ended_reason: "idle"`). `start(metadata=None, *, idle_timeout_secs=None)` sets a
session's own timeout (`0` = never) and `touch()` keeps it open. `memories()` leaves out the
sentence sub-memories the server derives from each memory (`include_derived=True` keeps them).
`get()`, `list(active_only=False)` and `end()` complete the API.

## `DakeraKnowledgeGraph`

Links an agent's memories and queries the resulting graph: paths, neighbourhoods, summaries
and deduplication. Constructor: `api_url`, `agent_id`, `api_key`.

```python
from autogen_dakera import DakeraKnowledgeGraph, DakeraMemory

memory = DakeraMemory(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")
kg = DakeraKnowledgeGraph(api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent")

a = memory.add("Anna leads the platform team in Berlin")["id"]
b = memory.add("The platform team ships every Friday")["id"]
kg.link(a, b, label="team")
print(kg.find_path(a, b)["hop_count"])
print(kg.query(root_id=a, max_depth=2)["edge_count"])
print(kg.summarize([a, b])["summary_memory"]["content"])  # stores a summary memory
print(kg.deduplicate(dry_run=True))  # report near-duplicate memories
```

`build(memory_id, depth=None)` expands the graph around a memory and `export()` returns the
whole graph.

## `DakeraEntityExtractor`

Named-entity extraction, and the extraction settings applied to the agent's memories as they
are stored. Constructor: `api_url`, `agent_id`, `api_key`.

```python
from autogen_dakera import DakeraEntityExtractor

entities = DakeraEntityExtractor(
    api_url="http://localhost:3000", api_key="dk-mykey", agent_id="my-agent"
)
entities.configure(["person", "location"])  # extraction for this agent's memories
print(entities.extract("Anna lives in Berlin"))
```

`memory_entities(memory_id)` returns the entities found in a stored memory.

## `DakeraNamespaceManager`

Creates and configures Dakera namespaces (vector collections) for your own data. An agent's
memories live in the namespace `_dakera_agent_{agent_id}`, which the server creates on the
first stored memory. Constructor: `api_url`, `api_key`.

```python
from autogen_dakera import DakeraNamespaceManager

namespaces = DakeraNamespaceManager(api_url="http://localhost:3000", api_key="dk-mykey")
namespaces.create("product-docs", dimensions=384)  # dimensions is required
print(namespaces.get("product-docs"))
namespaces.delete("product-docs")
```

`list()`, `stats(name)` and `configure(name, dimension=, distance=None)` complete the API.

## Configuration

Every class takes `api_url` and `api_key` explicitly. Read them from the environment rather
than hard-coding them — the examples use these variables:

| Variable | Used by | Description |
|---|---|---|
| `DAKERA_API_URL` | the examples | Dakera server URL (default `http://localhost:3000`) |
| `DAKERA_API_KEY` | `DakeraAutoGenMemory` (when `api_key` is not given), the examples | API key |
| `OPENAI_API_KEY` | `assistant_agent.py` | Optional: use OpenAI instead of the replay client |

```python
import os

from autogen_dakera import DakeraAutoGenMemory

memory = DakeraAutoGenMemory(
    api_url=os.environ.get("DAKERA_API_URL", "http://localhost:3000"),
    agent_id="my-agent",  # api_key defaults to $DAKERA_API_KEY
)
```

The server's root key is set with `DAKERA_ROOT_API_KEY` when it starts; keys scoped to
namespaces can be created with it (see the [Dakera docs](https://dakera.ai/docs)).

## Examples

| Script | Shows | LLM key? |
|---|---|---|
| [`assistant_agent.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/assistant_agent.py) | An `AssistantAgent` with `DakeraAutoGenMemory` | Optional (replay client without one) |
| [`basic_memory.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/basic_memory.py) | Store and recall with `DakeraMemory` | No |
| [`advanced_memory.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/advanced_memory.py) | Importance, tag filters, event time, consolidation | No |
| [`batch_operations.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/batch_operations.py) | Batch recall and forget | No |
| [`conversation_history.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/conversation_history.py) | Conversation turns as long-term memory | No |
| [`hybrid_search.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/hybrid_search.py) | Semantic recall vs. vector + BM25 search | No |
| [`knowledge_graph.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/knowledge_graph.py) | Links, graph queries, paths, summaries | No |
| [`sessions.py`](https://github.com/Dakera-AI/dakera-autogen/blob/main/examples/sessions.py) | Sessions, idle timeout and `touch()` | No |

```bash
export DAKERA_API_URL=http://localhost:3000
export DAKERA_API_KEY=dk-mykey
python examples/assistant_agent.py
```

## Troubleshooting

- **`dakera.ConnectionError` / connection refused** — the server is not running or not on that
  port. The docs use port 3000 (`-p 3000:3000`); this repository's CI publishes it on 3300.
  Check with `curl http://localhost:3000/health`.
- **`dakera.AuthenticationError` (401)** — the key does not match the server's
  `DAKERA_ROOT_API_KEY` (or a key created with it). `DakeraAutoGenMemory` reads
  `DAKERA_API_KEY` when `api_key` is not given, and always after `load_component()`.
- **`AttributeError: ... has no attribute 'update_context'`** — `DakeraMemory` was passed to
  `AssistantAgent(memory=[...])`. Use `DakeraAutoGenMemory`; `DakeraMemory` is the
  synchronous helper. `ImportError: autogen_core` means the `autogen` extra is not installed.
- **Nothing recalled for a new agent** — an agent that has stored nothing recalls nothing. A
  server before v0.12.3 answers such a recall with 404 `NAMESPACE_NOT_FOUND` for some queries
  (v0.12.3 answers an empty list); `DakeraAutoGenMemory` (`query()`, `update_context()`,
  `clear()`) and `DakeraMemory` (`query()`, `batch_query()`, `hybrid_search()`) treat it as no
  memories, so a new agent starts the same way on every v0.12 server. Other 404s are raised.
- **Fewer results than expected, or none of the "context" the server returns** — recall
  returns at most `top_k` ranked memories. A v0.12.3 server can add a session's neighbouring
  memories after the ranked results; this package requests them separately and leaves them out.
- **`event_time` / `idle_timeout_secs` seem to have no effect** — they need server v0.12.3 /
  v0.12.2; older servers ignore them. `GET /health` reports the server version.

## Development

```bash
pip install -e ".[dev,autogen]"
pytest tests/ -v                             # unit tests; live tests need DAKERA_API_URL
ruff check . && ruff format --check . && mypy src/
```

See [CONTRIBUTING.md](https://github.com/Dakera-AI/dakera-autogen/blob/main/CONTRIBUTING.md)
for the live tests against a local server and the pull request process.

## Related packages

| Package | What it is |
|---|---|
| [`dakera`](https://pypi.org/project/dakera/) · [`@dakera-ai/dakera`](https://www.npmjs.com/package/@dakera-ai/dakera) · [`dakera-client`](https://crates.io/crates/dakera-client) · [`dakera-go`](https://github.com/Dakera-AI/dakera-go) | Python, TypeScript, Rust and Go SDKs |
| [`langchain-dakera`](https://pypi.org/project/langchain-dakera/) | LangChain (Python): memory, vector store, sessions, knowledge graph |
| [`@dakera-ai/langchain`](https://www.npmjs.com/package/@dakera-ai/langchain) | LangChain.js: memory, vector store, sessions, knowledge graph |
| [`llamaindex-dakera`](https://pypi.org/project/llamaindex-dakera/) | LlamaIndex: memory block, vector store, memory store |
| **[`autogen-dakera`](https://pypi.org/project/autogen-dakera/)** | **AutoGen: `Memory` for `AssistantAgent`, sessions, knowledge graph** |
| [`crewai-dakera`](https://pypi.org/project/crewai-dakera/) | CrewAI: storage for a crew's memories |
| [`strands-dakera`](https://pypi.org/project/strands-dakera/) | Strands Agents: memory tool and `MemoryStore` |
| [`@dakera-ai/ai-sdk`](https://www.npmjs.com/package/@dakera-ai/ai-sdk) | Vercel AI SDK: memory middleware and tools |

## Links

- [dakera.ai](https://dakera.ai) · [Documentation](https://dakera.ai/docs) · [LoCoMo benchmark](https://dakera.ai/benchmark) · [AutoGen integration guide](https://dakera.ai/integrations/autogen.html)
- Self-hosting: [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy) (Docker Compose, Kubernetes) · [dakera-helm](https://github.com/Dakera-AI/dakera-helm) · server image `ghcr.io/dakera-ai/dakera`
- Tools: [dakera-mcp](https://github.com/Dakera-AI/dakera-mcp) (MCP server) · [dakera-cli](https://github.com/Dakera-AI/dakera-cli) (`dk` command line)
- [Issues](https://github.com/Dakera-AI/dakera-autogen/issues) · [Changelog](https://github.com/Dakera-AI/dakera-autogen/blob/main/CHANGELOG.md)

## License

[MIT](https://github.com/Dakera-AI/dakera-autogen/blob/main/LICENSE) © [Dakera AI](https://dakera.ai)
