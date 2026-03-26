.PHONY: install install-extension install-python uninstall clean

install: install-extension install-python ## Install everything (extension + Python client)
	@echo ""
	@echo "✓ Done! Reload VS Code (Cmd/Ctrl+Shift+P → 'Reload Window'), then:"
	@echo '  python -c "from copilot_proxy import ask; print(ask(\"Hello\"))"'

install-extension: ## Build and install the VS Code extension
	cd vscode-extension && npm install --no-audit --no-fund
	cd vscode-extension && npm run compile
	cd vscode-extension && npx @vscode/vsce package --allow-missing-repository -o copilot-proxy.vsix
	code --install-extension vscode-extension/copilot-proxy.vsix --force

install-python: ## Install the Python client (editable)
	pip install -e .

uninstall: ## Uninstall extension and Python package
	code --uninstall-extension undefined_publisher.copilot-proxy || true
	pip uninstall -y copilot-proxy || true

clean: ## Remove build artifacts
	rm -rf vscode-extension/out vscode-extension/node_modules vscode-extension/*.vsix
	rm -rf build dist *.egg-info src/*.egg-info
