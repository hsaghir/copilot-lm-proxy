# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-03-26

### Changed
- Renamed PyPI package to `copilot-lm-proxy` (import unchanged: `from copilot_proxy import ask`)
- Configurable port via VS Code settings (`copilot-proxy.port`)
- Configurable URL via `COPILOT_PROXY_URL` environment variable

### Added
- Status bar indicator (running / standby / stopped / error)
- Multi-window support with automatic standby and takeover
- Smart port conflict handling with health checks
- `/health` endpoint for liveness checks
- `is_running()` helper function
- Error hierarchy: `CopilotProxyError`, `ProxyConnectionError`, `ModelNotFoundError`
- OpenAI-compatible `/v1/models` response format
- Request validation and client disconnect handling
- `py.typed` marker for PEP 561
- GitHub Actions CI and PyPI publish workflows
- Issue templates, CHANGELOG, SECURITY, CODE_OF_CONDUCT
- `.editorconfig` and ruff configuration
- Demo SVG in README

## [0.1.0] - 2025-03-26

### Added
- VS Code extension: HTTP proxy server exposing Copilot's Language Model API
- Python client library with `ask()`, `chat()`, `list_models()`, `is_running()`
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`)
- Streaming support (Server-Sent Events)
- Structured output with Pydantic (optional dependency)
- Status bar indicator (running / standby / stopped / error)
- Multi-window support: standby mode with automatic takeover
- Smart port conflict handling with health checks
- Error hierarchy: `CopilotProxyError`, `ProxyConnectionError`, `ModelNotFoundError`
- GitHub Actions CI (Python 3.10–3.13 + extension compile)
- Unit tests (24) and integration tests (5)
