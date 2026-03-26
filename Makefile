.PHONY: install install-extension install-python uninstall clean test

install: install-extension install-python ## Install everything (extension + Python client)
	@echo ""
	@echo "✓ Done! Reload VS Code (Cmd/Ctrl+Shift+P → 'Reload Window'), then:"
	@echo '  python -c "from copilot_proxy import ask; print(ask(\"Hello\"))"'

install-extension: ## Build and install the VS Code extension
	cd vscode-extension && npm install --no-audit --no-fund
	cd vscode-extension && npm run compile
	cd vscode-extension && npx @vscode/vsce package --allow-missing-repository -o copilot-lm-proxy.vsix
	code --install-extension vscode-extension/copilot-lm-proxy.vsix --force

install-python: ## Install the Python client (editable)
	pip install -e ".[dev]"

test: ## Run unit tests
	pytest tests/test_client.py -v

test-all: ## Run all tests (requires proxy running)
	pytest -v

test-cov: ## Run tests with coverage report
	pytest tests/test_client.py --cov=copilot_proxy --cov-report=term-missing -v

uninstall: ## Uninstall extension and Python package
	code --uninstall-extension hsaghir.copilot-lm-proxy || true
	pip uninstall -y copilot-lm-proxy || true

clean: ## Remove build artifacts
	rm -rf vscode-extension/out vscode-extension/node_modules vscode-extension/*.vsix
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
