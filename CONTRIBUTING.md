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

**Do not open public issues for security vulnerabilities.** See [SECURITY.md](.github/SECURITY.md) for responsible disclosure instructions — email security@dakera.ai.

## Pull Request Process

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b fix/your-fix-name
   ```
2. Make your changes and ensure tests pass
3. Open a pull request against `main` with a clear description

## Development Setup

**Prerequisites:** Python 3.8+, a running Dakera server (for integration tests)

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests (unit only — no server required)
pytest tests/ -v

# Lint
ruff check .

# Type check
mypy src/

# Format check
ruff format --check .
```

## Code Style

- **Formatter**: `ruff format` — all code must be formatted
- **Linter**: `ruff check .` — no lint errors
- **Type checker**: `mypy src/` — all public APIs must be typed
- **Tests**: `pytest` — all tests must pass; new features require tests

## Testing Against a Live Dakera Server

Some scenarios require a running Dakera instance. Start one locally with Docker:

```bash
docker run -p 3300:3300 ghcr.io/dakera-ai/dakera:latest
```

Then set the server URL in your test environment:

```bash
export DAKERA_SERVER_URL=http://localhost:3300
pytest tests/integration/ -v
```

For unit tests that do not require a live server, mock the `dakera` client:

```python
from unittest.mock import patch, MagicMock

with patch("dakera_autogen.memory.Dakera") as mock_client:
    mock_client.return_value.store.return_value = MagicMock(id="mem-123")
    # test your logic
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
