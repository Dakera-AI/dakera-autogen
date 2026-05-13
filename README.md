# autogen-dakera

[![PyPI](https://img.shields.io/pypi/v/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/autogen-dakera)](https://pypi.org/project/autogen-dakera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AutoGen integration for the [Dakera AI](https://dakera.ai) memory platform.**

Give your AutoGen agents persistent, semantically-recalled memory backed by Dakera.

## Installation

```bash
pip install autogen-dakera
```

## Quick Start

```python
from autogen_dakera import DakeraMemory
from autogen_agentchat.agents import AssistantAgent

memory = DakeraMemory(
    api_url="https://your-dakera-instance.com",
    api_key="dk-...",
    agent_id="my-agent",
)
agent = AssistantAgent(name="assistant", memory=[memory], model_client=...)
```

## Links

- [Dakera Documentation](https://docs.dakera.ai/integrations/autogen)
- [Dakera AI](https://dakera.ai)
