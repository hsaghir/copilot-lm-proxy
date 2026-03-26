# Contributing to Copilot Proxy

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/hsaghir/copilot-lm-proxy.git
cd copilot-lm-proxy

# Install Python package with dev dependencies
pip install -e ".[dev]"

# Install VS Code extension
cd vscode-extension && npm install && npm run compile && cd ..
```

## Running Tests

```bash
# Unit tests (no proxy needed)
pytest tests/test_client.py -v

# Integration tests (requires proxy running in VS Code)
pytest tests/test_integration.py -v

# All tests with coverage
pytest --cov=copilot_proxy -v
```

## Project Structure

```
copilot-proxy/
├── src/copilot_proxy/      # Python client library (zero dependencies)
│   ├── __init__.py          # Public API exports
│   └── client.py            # CopilotClient implementation
├── vscode-extension/        # VS Code extension (HTTP proxy server)
│   └── src/extension.ts     # Extension entry point
├── tests/                   # Test suite
│   ├── test_client.py       # Unit tests (mock server)
│   └── test_integration.py  # Integration tests (live proxy)
├── examples/                # Usage examples
├── pyproject.toml           # Python package config
└── Makefile                 # Build automation
```

## Making Changes

1. Fork the repo and create a feature branch.
2. Make your changes.
3. Add or update tests as needed.
4. Run `pytest tests/test_client.py -v` to verify.
5. Submit a pull request.

## Code Style

- Python: follow standard PEP 8 conventions.
- TypeScript: follow the existing style in the extension.
- Keep dependencies minimal — the Python client uses only stdlib.
