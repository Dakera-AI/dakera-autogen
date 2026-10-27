"""An AutoGen AssistantAgent with persistent Dakera memory.

DakeraAutoGenMemory implements AutoGen's ``Memory`` interface: before every model
call the agent recalls the memories most relevant to the conversation and adds them
to the model context. The memories live on the Dakera server, so a new agent (or a
new process) given the same ``agent_id`` remembers them.

With ``OPENAI_API_KEY`` set the agent uses gpt-4o-mini; without it a replay model
client stands in, so the example runs without a model provider and shows what the
model is sent.

Usage:
    export DAKERA_API_URL="http://localhost:3000"
    export DAKERA_API_KEY="dk-..."          # optional
    export OPENAI_API_KEY="sk-..."          # optional
    pip install "autogen-dakera[autogen]" "autogen-ext[openai]"
    python assistant_agent.py
"""

import asyncio
import os
import textwrap

from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.replay import ReplayChatCompletionClient

from autogen_dakera import DakeraAutoGenMemory

api_url = os.environ.get("DAKERA_API_URL", "http://localhost:3000")
api_key = os.environ.get("DAKERA_API_KEY", "")


def model_client() -> ChatCompletionClient:
    if os.environ.get("OPENAI_API_KEY"):
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(model="gpt-4o-mini")
    return ReplayChatCompletionClient(
        ["Pack for about 12 °C and rain; take the U2 from the airport, not a taxi."]
    )


async def main() -> None:
    memory = DakeraAutoGenMemory(
        api_url=api_url, agent_id="autogen-assistant-demo", api_key=api_key, recall_k=3
    )

    # What the agent should know about the user, e.g. collected in an earlier session.
    for fact in [
        "The user prefers metric units",
        "The user is travelling to Berlin next week",
        "The user avoids taxis and takes public transport",
    ]:
        await memory.add(MemoryContent(content=fact, mime_type=MemoryMimeType.TEXT))
    # JSON memories are stored as text and come back as dicts.
    await memory.add(
        MemoryContent(content={"home_airport": "LYS"}, mime_type=MemoryMimeType.JSON),
    )

    client = model_client()
    agent = AssistantAgent(
        name="travel_assistant",
        model_client=client,
        memory=[memory],
        system_message="You are a travel assistant. Use what you know about the user.",
    )
    result = await agent.run(task="What should I pack, and how do I get into the city?")

    for message in result.messages:
        if message.type == "MemoryQueryEvent":
            print("Recalled before answering:")
            for item in message.content:
                print(f"  [{item.metadata['score']:.3f}] {item.content}")
    print(f"\nAgent: {result.messages[-1].content}")

    if isinstance(client, ReplayChatCompletionClient):
        print("\nSystem messages sent to the (replay) model:")
        for sent in client.create_calls[0]["messages"]:
            if sent.type == "SystemMessage":
                print(textwrap.indent(sent.content.strip(), "  "))

    # Forget everything this demo stored, so a rerun starts from scratch.
    await memory.clear()
    await memory.close()
    await client.close()


asyncio.run(main())
