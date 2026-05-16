# autogen-dakera

[![CI](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml/badge.svg)](https://github.com/Dakera-AI/dakera-autogen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-dakera.ai-D4A843)](https://dakera.ai/docs)

**Persistent, semantically-recalled memory for [AutoGen](https://microsoft.github.io/autogen/) agents, powered by [Dakera](https://github.com/Dakera-AI/dakera-deploy).**

Your AutoGen agents remember everything — across sessions, across restarts. Dakera handles embedding, storage, and retrieval server-side with no local model required.

---

## Quick Start

### Step 1 — Run Dakera

Dakera is a self-hosted memory server. Spin it up with Docker:

```bash
docker run -d \
  --name dakera \
  -p 3300:3300 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:latest
```

For a production setup with persistent storage, use Docker Compose:

```bash
# Download and start
curl -sSfL https://raw.githubusercontent.com/Dakera-AI/dakera-deploy/main/docker-compose.yml \
  -o docker-compose.yml
DAKERA_API_KEY=dk-mykey docker compose up -d

# Verify it's running
curl http://localhost:3300/health
```

> Full deployment guide: [github.com/Dakera-AI/dakera-deploy](https://github.com/Dakera-AI/dakera-deploy)

### Step 2 — Install the integration

```bash
pip install autogen-dakera
```

### Step 3 — Add memory to your agent

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_dakera import DakeraMemory

memory = DakeraMemory(
    api_url="http://localhost:3300",
    api_key="dk-mykey",
    agent_id="my-agent",
)

model_client = OpenAIChatCompletionClient(model="gpt-4o")

agent = AssistantAgent(
    name="assistant",
    model_client=model_client,
    memory=[memory],
)

# Agent now persists what it learns across sessions
```

---

## Installation

```bash
# Core + integration
pip install autogen-dakera

# With AutoGen (if not already installed)
pip install "autogen-dakera[autogen]"
```

**Requirements:** Python ≥ 3.10, a running Dakera server (see Step 1 above)

---

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_url` | `str` | — | Dakera server URL (e.g. `http://localhost:3300`) |
| `api_key` | `str` | `""` | API key set via `DAKERA_ROOT_API_KEY` |
| `agent_id` | `str` | — | Logical identifier for this agent's memory |
| `min_importance` | `float` | `0.0` | Minimum importance score for recalled memories |
| `top_k` | `int` | `5` | Number of memories to surface per query |

---

## Examples

### Multi-agent team with shared memory

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_dakera import DakeraMemory

async def main():
    shared_memory = DakeraMemory(
        api_url="http://localhost:3300",
        api_key="dk-mykey",
        agent_id="research-team",
        top_k=8,
    )

    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    researcher = AssistantAgent(
        name="researcher",
        model_client=model_client,
        memory=[shared_memory],
        system_message="You are a research expert. Remember key findings.",
    )

    analyst = AssistantAgent(
        name="analyst",
        model_client=model_client,
        memory=[shared_memory],
        system_message="You are a data analyst. Build on what the researcher found.",
    )

    team = RoundRobinGroupChat(
        [researcher, analyst],
        termination_condition=MaxMessageTermination(max_messages=6),
    )

    # First session — agents learn and store
    result = await team.run(task="Research AI memory architectures")
    print(result.messages[-1].content)

    # Later session — agents recall prior research
    result = await team.run(task="What do we know about transformer memory?")
    print(result.messages[-1].content)

asyncio.run(main())
```

### Filtering memories by importance

```python
memory = DakeraMemory(
    api_url="http://localhost:3300",
    api_key="dk-mykey",
    agent_id="my-agent",
    min_importance=0.7,  # only surface high-quality memories
    top_k=3,
)
```

---

## How it works

1. During conversation, AutoGen calls `DakeraMemory.add()` with new messages
2. Dakera embeds the content server-side and stores it with a semantic vector
3. Before each agent response, AutoGen calls `DakeraMemory.query()` — Dakera performs hybrid search and returns the most relevant past memories
4. Memories are injected into the agent's context automatically

---

## Related packages

| Package | Framework | Language |
|---------|-----------|----------|
| `crewai-dakera` | CrewAI | Python |
| `langchain-dakera` | LangChain | Python |
| `llamaindex-dakera` | LlamaIndex | Python |
| `@dakera-ai/langchain` | LangChain.js | TypeScript |

---

## Links

- [Dakera Server](https://github.com/Dakera-AI/dakera-deploy) — self-hosted memory server
- [Dakera Python SDK](https://github.com/Dakera-AI/dakera-py) — low-level API client
- [Integration guide](https://dakera.ai/integrations/autogen.html) — full setup walkthrough
- [All integrations](https://dakera.ai/integrations/)

---

## License

MIT © [Dakera AI](https://dakera.ai)
