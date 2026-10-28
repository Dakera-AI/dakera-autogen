# Contributing to dakera-autogen

Thank you for your interest in contributing to the Dakera AutoGen integration! This guide covers everything you need to get started.

## Reporting Bugs

Use the [Bug Report](https://github.com/Dakera-AI/dakera-autogen/issues/new?template=bug_report.md) template. Please include:
- A clear description of the bug and steps to reproduce
- Your Python, AutoGen, and dakera-autogen versions
- Whether you are connecting to a local or hosted Dakera instance
- Relevant error messages or tracebacks

## Suggesting Features

Use the [Feature Request](https://github.com/Dakera-AI/dakera-autogen/issues/new?template=feature_request.md) template. Describe the problem you are solving, your proposed solution, and any alternatives you have considered.

## Security Vulnerabilities

**Do not open public issues for security vulnerabilities.** See [SECURITY.md](.github/SECURITY.md) for responsible disclosure instructions — report via [GitHub Security Advisories](https://github.com/dakera-ai/dakera-autogen/security/advisories/new).

## Pull Request Process

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b fix/your-fix-name
   ```
2. Make your changes and ensure tests pass
3. Open a pull request against `main` with a clear description

## Development Setup

**Prerequisites:** Python 3.10+, Docker (for the live tests and examples)

```bash
# Install in development mode, with AutoGen and the test tools
pip install -e ".[dev,autogen]"

# Unit tests (no server needed; the live tests are skipped)
pytest tests/ -v

# Lint, format check, type check
ruff check .
ruff format --check .
mypy src/
```

## Code Style

- **Formatter**: `ruff format` — all code must be formatted (CI checks it)
- **Linter**: `ruff check .` — no lint errors
- **Type checker**: `mypy src/` — all public APIs must be typed and documented
- **Tests**: `pytest` — all tests must pass; new features need unit tests and, when they
  call the server, a live test in `tests/test_integration.py`

## Testing Against a Live Dakera Server

`tests/test_integration.py` runs every class against a real server and is skipped unless
`DAKERA_API_URL` is set. Start the server version CI uses:

```bash
docker run -d --name dakera -p 3000:3000 -e DAKERA_AUTH_ENABLED=false \
  ghcr.io/dakera-ai/dakera:0.12.3
curl http://localhost:3000/health

export DAKERA_API_URL=http://localhost:3000
pytest tests/ -v                    # unit + live tests
python examples/assistant_agent.py  # each example runs against the same server
```

With authentication enabled (`-e DAKERA_ROOT_API_KEY=dk-mykey` instead of
`DAKERA_AUTH_ENABLED=false`), also export `DAKERA_API_KEY=dk-mykey`.

Unit tests mock the SDK client with `create_autospec`, so a call that does not match the
`dakera` SDK's signature fails the test:

```python
from unittest.mock import create_autospec, patch

from dakera import DakeraClient

from autogen_dakera import DakeraMemory

with patch("autogen_dakera.memory.DakeraClient") as MockClient:
    client = create_autospec(DakeraClient, instance=True)
    MockClient.return_value = client
    memory = DakeraMemory(api_url="http://localhost:3000", agent_id="agent-1")
    memory.add("Project deadline is April 15")
    client.store_memory.assert_called_once()
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
