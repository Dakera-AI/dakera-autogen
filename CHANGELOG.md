# Changelog

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
