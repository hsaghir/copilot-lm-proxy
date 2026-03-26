# Changelog

All notable changes to this project will be documented in this file.

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
