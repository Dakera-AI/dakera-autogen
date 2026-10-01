# Changelog

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
