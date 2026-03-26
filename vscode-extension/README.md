# Copilot Proxy VS Code Extension

Exposes GitHub Copilot's LLM API via a local HTTP server.

## Installation

```bash
npm install
npm run compile
npx @vscode/vsce package -o copilot-lm-proxy.vsix
code --install-extension copilot-lm-proxy.vsix
```

## Usage

The extension auto-starts when VS Code loads. Server runs on `http://127.0.0.1:19823`.

### Commands

- `Copilot Proxy: Start Server` - Start the proxy server
- `Copilot Proxy: Stop Server` - Stop the proxy server
