# Changelog

## [0.4.0] - 2026-10-27

Dakera server **v0.12.3** support and a real AutoGen `Memory`. Requires the `dakera` Python
SDK **>= 0.14.1**; tested against Dakera server v0.12.3 and still works with v0.12.0 – v0.12.2
(the new arguments below need the server version named next to them).

### Changed
- Requires `dakera>=0.14.1` (was `>=0.13.1`).
- `DakeraMemory.query()` and `DakeraMemory.batch_query()` return at most `top_k` ranked memories. A v0.12.3
  server appends neighbourhood context to a recall by default, which could push the result
  past `top_k` and mix in items whose scores are not comparable with the ranked ones; the
  context is now requested separately (`neighborhood_mode="separate"`) and left out.
- Result `score` is the server's `rank_score` (v0.12.3), the field recall ranks by; older
  servers keep the previous score.
- `DakeraMemory.query()` results carry the memory's `importance`.

### Added
- **`DakeraAutoGenMemory`**, an implementation of AutoGen's `autogen_core.memory.Memory`, so a
  Dakera agent's memories can be given to `AssistantAgent(memory=[...])`: `add()` stores a
  `MemoryContent` (text, Markdown or JSON; images and binary raise `ValueError`), `query()`
  returns at most `top_k` ranked memories as `MemoryContent` with `id` / `score` /
  `importance` in their metadata, `update_context()` adds the memories relevant to the last
  message as one system message, `clear()` deletes the agent's memories and `close()` closes
  the connections. It is an AutoGen component (`DakeraAutoGenMemoryConfig`) that round-trips
  through `dump_component()` / `load_component()`; the API key is never serialized and
  defaults to `DAKERA_API_KEY`. Requests honour AutoGen's `CancellationToken`.
- The `autogen` extra installs `autogen-core` / `autogen-agentchat` >= 0.4.3 (the first release
  with `autogen_core.memory`) and the async `dakera` client (`dakera[async]`).
- `DakeraMemory.add(..., event_time=)`: when the memory's event happened (Unix seconds, an RFC 3339
  string or a timezone-aware `datetime`) for history written after the fact. Server v0.12.3
  reads it for recency and `since` / `until`; `created_at` stays the ingest time.
- `DakeraMemory.consolidate(memory_ids=None)`: merge exactly the given memories (at least two).
- `DakeraSessionManager.start(metadata=None, *, idle_timeout_secs=None)` and
  `DakeraSessionManager.touch()`: from v0.12.2 the server ends a session after 4 h without
  activity by default; set the session's own timeout (`0` = never) or keep it open.
  `DakeraSessionManager.get()` returns `ended_reason` (`"client"`, `"idle"`, ...) and
  `last_activity_at`; `DakeraSessionManager.list()` returns `ended_reason`.
- `DakeraSessionManager.memories(session_id, *, include_derived=False)`.
- `examples/assistant_agent.py`: an `AssistantAgent` with `DakeraAutoGenMemory`; it uses
  OpenAI when `OPENAI_API_KEY` is set and a replay model client otherwise.
- `LICENSE` (MIT, as declared in `pyproject.toml`).

### Fixed
- The README's headline example passed `DakeraMemory` to `AssistantAgent(memory=[...])`, but
  `DakeraMemory` is not an AutoGen `Memory`, so the agent failed at its first model call
  (`AttributeError: ... has no attribute 'update_context'`). The README now uses
  `DakeraAutoGenMemory`, and every README snippet is run against a live server.
- `DakeraSessionManager.memories()` returned the sentence sub-memories the server derives from
  a session's memories (tagged `dakera-curated`) alongside them; they are left out unless
  `include_derived=True`.
- README: the `docker run` quick start published port 3300 while the server listens on 3000;
  the Docker Compose URL pointed at a file that does not exist and set `DAKERA_API_KEY`
  instead of the required `DAKERA_ROOT_API_KEY`; the configuration table named a `top_k`
  constructor argument (it is `recall_k`).
- The `advanced_memory.py` example printed `importance`, which `query()` did not return; it
  now queries something the stored memories answer and shows `event_time`.

### Docs / examples
- README rewritten around `DakeraAutoGenMemory`, with sections for `DakeraMemory`, sessions,
  the knowledge graph and entities, and an examples table. CONTRIBUTING describes the current
  commands and how to run the live tests (`DAKERA_API_URL`).
- Examples default to `http://localhost:3000` (the server's default port), forget what they
  store so reruns start clean, and cover tag filters, consolidation, links and paths,
  `touch()` and the session context manager.

### Tests / CI
- `tests/test_integration.py`: live tests of every class against a real server, skipped unless
  `DAKERA_API_URL` is set (the CI integration job sets it).
- Integration tests and examples run against `ghcr.io/dakera-ai/dakera:0.12.3`. That image ships
  no `curl`, so the service container has no in-container health check; the job polls
  `/health` from the runner instead.
- CI installs the `autogen` extra, checks formatting (`ruff format --check`, the whole tree is
  formatted), and a failing example now fails the examples job.

## [0.3.0] - 2026-10-01

Dakera server **v0.12.0** support. Requires the `dakera` Python SDK **>= 0.13.1**; compatible
with Dakera server v0.12.0 and v0.11.108.

### Changed
- Requires `dakera>=0.13.1` (was `>=0.9.0`).
- `DakeraEntityExtractor.configure(entity_types=None, *, extract_entities=True)` configures the
  agent's memory namespace (`_dakera_agent_{agent_id}`), the namespace whose settings apply when
  memories are stored. It previously targeted a namespace named after the agent id (a 404 on the
  server) and could not succeed because the required `extract_entities` argument was never sent.
- `DakeraNamespaceManager.configure(name, *, dimension, distance=None)`: `dimension` is required
  by the server and is now an explicit argument (the old `**kwargs` pass-through could not work
  without it).
- `DakeraKnowledgeGraph.link(source_id, target_id, *, label=None)` sends the agent id the server
  requires (every link was a 422 before) and returns the server's `{from_id, to_id, edge_type}`.
  The `edge_type` argument is gone: the server records every explicit link as `linked_by`.
- `DakeraKnowledgeGraph.summarize(memory_ids, *, target_type=None)` needs at least two ids and has
  no `dry_run`: the server has no dry run and always stores the summary (dakera 0.13.1 raises on
  `dry_run=True` rather than silently writing).
- `DakeraKnowledgeGraph.build(memory_id, depth=None)`: the seed `memory_id` is required by the server.
- `DakeraMemory.query(tags=...)` works: dakera 0.13.1 `recall()` accepts `tags` (it raised
  `TypeError` before).

### Fixed
- `DakeraSessionManager.list()` reads the server's `{"sessions": [...]}` answer (it iterated over
  the object's keys and failed).
- `DakeraNamespaceManager.stats()` works: dakera 0.13.0 reads `GET /v1/namespaces/{ns}`
  (older SDKs called a route the server does not serve).
- The `knowledge_graph.py` example stores two memories and summarizes them.

### Tests / CI
- Unit tests mock the client with `create_autospec(DakeraClient)`, so a call that does not match
  the SDK's signature fails the test.
- Integration tests and examples run against `ghcr.io/dakera-ai/dakera:0.12.0` instead of `latest`.

## [0.1.1] - 2026-05-13

### Added
- **`__repr__` for `DakeraMemory`**: meaningful string representation for easier debugging in AutoGen pipelines
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`, issue templates, PR template

### Changed
- Bumped GitHub Actions: `actions/checkout` v4 → v6, `actions/setup-python` v5 → v6

## [0.1.0] - 2026-05-13

### Added
- Initial release — AutoGen integration for Dakera AI memory platform
- `DakeraMemory` class implementing AutoGen's `Memory` protocol for persistent agent memory
- PyPI publish via OIDC Trusted Publisher
