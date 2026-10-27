"""DakeraAutoGenMemory — an ``autogen_core.memory.Memory`` backed by Dakera.

Needs the ``autogen`` extra (``pip install "autogen-dakera[autogen]"``).
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable
from datetime import datetime
from typing import Any, TypeVar

from autogen_core import CancellationToken, Component
from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from dakera import AsyncDakeraClient, NotFoundError
from dakera.models import BatchForgetRequest, BatchMemoryFilter
from pydantic import BaseModel, Field, SecretStr
from typing_extensions import Self

_T = TypeVar("_T")

# The metadata key that keeps a memory's MIME type, so ``query()`` returns the
# ``MemoryContent`` that was added.
MIME_TYPE_KEY = "mime_type"

_TEXT_MIME_TYPES = {
    MemoryMimeType.TEXT.value,
    MemoryMimeType.MARKDOWN.value,
    MemoryMimeType.JSON.value,
}


class DakeraAutoGenMemoryConfig(BaseModel):
    """Configuration of :class:`DakeraAutoGenMemory` (its AutoGen component config)."""

    api_url: str = Field(description="Dakera server URL, e.g. http://localhost:3000.")
    agent_id: str = Field(description="The Dakera agent whose memories are read and written.")
    api_key: SecretStr | None = Field(
        default=None,
        exclude=True,
        description="Dakera API key; never serialized (a loaded memory reads DAKERA_API_KEY).",
    )
    recall_k: int = Field(default=5, ge=1, description="Memories recalled per query.")
    min_importance: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Only recall memories at least this important."
    )
    importance: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Importance of added memories (the server default when unset).",
    )
    memory_type: str = Field(default="episodic", description="Memory type of added memories.")
    timeout: float = Field(default=30.0, gt=0, description="Per-request timeout in seconds.")


class DakeraAutoGenMemory(Memory, Component[DakeraAutoGenMemoryConfig]):
    """AutoGen memory backed by a Dakera agent: pass it to ``AssistantAgent(memory=[...])``.

    Before each model call the agent runs :meth:`update_context`, which recalls the
    memories most relevant to the last message and adds them to the model context as
    one system message. Memories persist on the Dakera server across runs, processes
    and agents: several AutoGen agents given the same ``agent_id`` share them.

    The agent does not store its conversation by itself; add what it should remember
    with :meth:`add` (AutoGen's ``MemoryContent``). Dakera embeds the text server-side,
    so no embedding model is needed in the client.

    Example:

        .. code-block:: python

            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.memory import MemoryContent

            memory = DakeraAutoGenMemory(api_url="http://localhost:3000", agent_id="assistant")
            fact = MemoryContent(content="The user prefers metric units", mime_type="text/plain")
            await memory.add(fact)
            agent = AssistantAgent("assistant", model_client=model_client, memory=[memory])

    Args:
        api_url: Dakera server URL.
        agent_id: The Dakera agent whose memories this memory reads and writes.
        api_key: Dakera API key; defaults to the ``DAKERA_API_KEY`` environment variable.
            It is left out of the component config, so a memory loaded with
            ``load_component()`` reads ``DAKERA_API_KEY``.
        recall_k: Memories recalled per query (default 5).
        min_importance: Only recall memories at least this important.
        importance: Importance of added memories (the server default when unset).
        memory_type: Memory type of added memories (default ``"episodic"``).
        timeout: Per-request timeout in seconds.
    """

    component_type = "memory"
    component_provider_override = "autogen_dakera.DakeraAutoGenMemory"
    component_config_schema = DakeraAutoGenMemoryConfig

    def __init__(
        self,
        api_url: str,
        agent_id: str,
        api_key: str | None = None,
        *,
        recall_k: int = 5,
        min_importance: float | None = None,
        importance: float | None = None,
        memory_type: str = "episodic",
        timeout: float = 30.0,
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("DAKERA_API_KEY")
        self._config = DakeraAutoGenMemoryConfig(
            api_url=api_url,
            agent_id=agent_id,
            api_key=SecretStr(api_key) if api_key else None,
            recall_k=recall_k,
            min_importance=min_importance,
            importance=importance,
            memory_type=memory_type,
            timeout=timeout,
        )
        self._client = AsyncDakeraClient(api_url, api_key=api_key or None, timeout=timeout)

    @property
    def agent_id(self) -> str:
        """The Dakera agent whose memories this memory reads and writes."""
        return self._config.agent_id

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        *,
        importance: float | None = None,
        memory_type: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
        event_time: int | float | str | datetime | None = None,
    ) -> None:
        """Store ``content`` as a memory of the agent.

        Text, Markdown and JSON content is stored (a ``dict`` as JSON); images and
        binary content raise ``ValueError``. ``content.metadata`` is stored with the
        memory, plus its MIME type under ``"mime_type"``.

        Args:
            content: The memory content to add.
            cancellation_token: Cancels the request.
            importance: Importance 0.0-1.0 (defaults to the memory's ``importance``).
            memory_type: Memory type (defaults to the memory's ``memory_type``).
            tags: Tags of the memory.
            session_id: A started Dakera session the memory belongs to.
            event_time: When the remembered event happened, for history written after
                the fact (Unix seconds, an RFC 3339 string or a timezone-aware
                ``datetime``); recency and time filters read it instead of the time
                of storage (server v0.12.3+).
        """
        text = _content_text(content)
        mime_type = (
            content.mime_type.value
            if isinstance(content.mime_type, MemoryMimeType)
            else content.mime_type
        )
        metadata = {**(content.metadata or {}), MIME_TYPE_KEY: mime_type}
        importance = importance if importance is not None else self._config.importance
        await _run(
            self._client.store_memory(
                self._config.agent_id,
                text,
                memory_type=memory_type or self._config.memory_type,
                importance=importance,
                metadata=metadata,
                session_id=session_id,
                tags=tags,
                event_time=event_time,
            ),
            cancellation_token,
        )

    async def query(
        self,
        query: str | MemoryContent = "",
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Recall the agent's memories most relevant to ``query``.

        Returns at most ``top_k`` ranked memories, most relevant first, with the MIME
        type they were added with (JSON content comes back as a ``dict``). Each result's
        metadata carries the stored metadata plus the Dakera ``id``, ``score`` (the
        server's ranking score) and ``importance``.

        Args:
            query: The query text (or a text ``MemoryContent``).
            cancellation_token: Cancels the request.
            **kwargs: ``top_k`` (default: ``recall_k``), ``min_importance``,
                ``memory_type`` and ``tags`` (memories carrying at least one of them).
        """
        text = query if isinstance(query, str) else _content_text(query)
        if not text.strip():
            return MemoryQueryResult(results=[])
        top_k = int(kwargs.pop("top_k", self._config.recall_k))
        min_importance = kwargs.pop("min_importance", self._config.min_importance)
        memory_type = kwargs.pop("memory_type", None)
        tags = kwargs.pop("tags", None)
        if kwargs:
            raise TypeError(f"unexpected query arguments: {sorted(kwargs)}")
        try:
            response = await _run(
                self._client.recall(
                    self._config.agent_id,
                    text,
                    top_k=top_k,
                    min_importance=min_importance,
                    memory_type=memory_type,
                    tags=tags,
                    neighborhood_mode="separate",
                ),
                cancellation_token,
            )
        except NotFoundError:
            # Servers before v0.12.3 answer 404 for an agent that has stored nothing.
            return MemoryQueryResult(results=[])
        results = []
        for memory in response.ranked[:top_k]:
            metadata = dict(memory.metadata or {})
            mime_type = metadata.pop(MIME_TYPE_KEY, MemoryMimeType.TEXT.value)
            metadata.update(id=memory.id, score=memory.score, importance=memory.importance)
            content: str | dict[str, Any] = memory.content
            if mime_type == MemoryMimeType.JSON.value:
                try:
                    content = json.loads(memory.content)
                except ValueError:
                    pass
            results.append(MemoryContent(content=content, mime_type=mime_type, metadata=metadata))
        return MemoryQueryResult(results=results)

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """Add the memories relevant to the last message to ``model_context``.

        The last message of the context is the query; the recalled memories are added
        as one system message listing them, most relevant first. Nothing is added when
        nothing is recalled.
        """
        messages = await model_context.get_messages()
        if not messages:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))
        result = await self.query(_message_text(messages[-1].content))
        if result.results:
            lines = [f"{i}. {_content_text(memory)}" for i, memory in enumerate(result.results, 1)]
            await model_context.add_message(
                SystemMessage(content="\nRelevant memories:\n" + "\n".join(lines))
            )
        return UpdateContextResult(memories=result)

    async def clear(self) -> None:
        """Delete every memory of the agent on the Dakera server. This cannot be undone."""
        try:
            await self._client.batch_forget(
                BatchForgetRequest(
                    agent_id=self._config.agent_id,
                    # The server refuses a filter without predicates; this one matches
                    # every memory.
                    filter=BatchMemoryFilter(min_importance=0.0),
                )
            )
        except NotFoundError:
            # Servers before v0.12.3 answer 404 for an agent that has stored nothing.
            pass

    async def close(self) -> None:
        """Close the HTTP connections. The memories stay on the server."""
        await self._client.close()

    def _to_config(self) -> DakeraAutoGenMemoryConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: DakeraAutoGenMemoryConfig) -> Self:
        return cls(
            api_url=config.api_url,
            agent_id=config.agent_id,
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            recall_k=config.recall_k,
            min_importance=config.min_importance,
            importance=config.importance,
            memory_type=config.memory_type,
            timeout=config.timeout,
        )

    def __repr__(self) -> str:
        return (
            f"DakeraAutoGenMemory(agent_id={self._config.agent_id!r}, "
            f"recall_k={self._config.recall_k})"
        )


async def _run(coro: Awaitable[_T], cancellation_token: CancellationToken | None) -> _T:
    """Await ``coro``, cancelled when ``cancellation_token`` is."""
    if cancellation_token is None:
        return await coro
    future = asyncio.ensure_future(coro)
    cancellation_token.link_future(future)
    return await future


def _content_text(content: MemoryContent) -> str:
    """The text Dakera stores for ``content``."""
    mime_type = (
        content.mime_type.value
        if isinstance(content.mime_type, MemoryMimeType)
        else content.mime_type
    )
    if isinstance(content.content, str) and (
        mime_type in _TEXT_MIME_TYPES or mime_type.startswith("text/")
    ):
        return content.content
    if isinstance(content.content, dict) and mime_type == MemoryMimeType.JSON.value:
        return json.dumps(content.content, ensure_ascii=False)
    raise ValueError(
        f"Dakera stores text memories: {type(content.content).__name__} content with MIME "
        f"type {mime_type!r} is not supported (use text/plain, text/markdown or "
        "application/json)"
    )


def _message_text(content: Any) -> str:
    """The text of a model-context message, used as the recall query."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Multimodal user content or function results: keep the text parts.
        parts = [
            item if isinstance(item, str) else getattr(item, "content", None) for item in content
        ]
        return "\n".join(part for part in parts if isinstance(part, str))
    return str(content)
