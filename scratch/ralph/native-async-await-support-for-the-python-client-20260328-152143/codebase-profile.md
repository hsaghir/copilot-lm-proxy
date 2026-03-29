# Codebase Profile

Project root: `/home/hsaghir/workspace/copilot-proxy`

## Project Configuration
- `pyproject.toml`
```
[project]
name = "copilot-lm-proxy"
version = "0.2.0"
description = "Python client for accessing GitHub Copilot LLMs via local proxy"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = []
classifiers = [
    "Development Status :: 4 - Beta",
```
- `Makefile`
```
.PHONY: install install-extension install-python uninstall clean test

install: install-extension install-python ## Install everything (extension + Python client)
	@echo ""
	@echo "✓ Done! Reload VS Code (Cmd/Ctrl+Shift+P → 'Reload Window'), then:"
	@echo '  python -c "from copilot_proxy import ask; print(ask(\"Hello\"))"'

install-extension: ## Build and install the VS Code extension
	cd vscode-extension && npm install --no-audit --no-fund
	cd vscode-extension && npm run compile
```

## Directory Structure
```
assets/
examples/
  basic_usage.py
  structured_output.py
scripts/
  gen_demo.py
  gen_demo_svg.py
src/
  copilot_proxy/
    __init__.py
    client.py
tests/
  __init__.py
  test_client.py
  test_integration.py
vscode-extension/
  out/
    extension.js
  src/
    extension.ts
  package-lock.json
  package.json
  README.md
  tsconfig.json
CHANGELOG.md
CODE_OF_CONDUCT.md
CONTRIBUTING.md
Makefile
pyproject.toml
README.md
SECURITY.md
```

## Test Commands
- `make test`
- `make test-all`
- `make test-cov`
- `pytest`
