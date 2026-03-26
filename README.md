# Copilot Proxy

Access GitHub Copilot's LLM models (Claude, GPT, Gemini) from any Python script via a local HTTP server.

## Quick Start

### 1. Install the VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
code --install-extension copilot-proxy-0.0.1.vsix
```

Then reload VS Code. The proxy starts automatically on `http://127.0.0.1:19823`.

### 2. Install the Python Client

```bash
pip install -e .
# or
uv add --editable /path/to/copilot-proxy
```

### 3. Use It

```python
from copilot_proxy import ask, chat, list_models

# Simple call (uses default model)
response = ask("Explain neural networks")

# Use a specific model
response = ask("Explain neural networks", model="claude-opus-4.5")

# Multi-turn conversation
response = chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"}
], model="gpt-4o")

# List all available models
models = list_models()
for m in models:
    print(f"{m['id']} ({m['vendor']})")
```

## Available Models

With a GitHub Copilot subscription, you get access to:

| Model | ID |
|-------|-----|
| Claude Opus 4.5 | `claude-opus-4.5` |
| Claude Sonnet 4.5 | `claude-sonnet-4.5` |
| Claude Sonnet 4 | `claude-sonnet-4` |
| Claude Haiku 4.5 | `claude-haiku-4.5` |
| GPT-4o | `gpt-4o` |
| GPT-4o Mini | `gpt-4o-mini` |
| GPT-5 | `gpt-5` |
| Gemini 2.5 Pro | `gemini-2.5-pro` |
| And more... | `list_models()` |

## API Reference

### Python Client

```python
from copilot_proxy import ask, chat, list_models, CopilotClient

# Simple question
ask(prompt: str, model: str | None = None) -> str

# Multi-turn chat
chat(messages: list[dict], model: str | None = None, stream: bool = False) -> str

# List available models
list_models() -> list[dict]

# Custom configuration
client = CopilotClient(base_url="http://127.0.0.1:19823")
client.ask("Hello")
```

### HTTP API

The proxy exposes an OpenAI-compatible API:

#### List Models

```bash
curl -X POST http://127.0.0.1:19823/v1/models
```

#### Chat Completion

```bash
curl -X POST http://127.0.0.1:19823/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Structured Output with Pydantic

```python
from pydantic import BaseModel
from copilot_proxy import ask
import json

class MovieReview(BaseModel):
    title: str
    rating: float
    summary: str

schema = MovieReview.model_json_schema()
prompt = f"Review Inception. Return JSON: {json.dumps(schema)}"

response = ask(prompt, model="claude-opus-4.5")
review = MovieReview.model_validate_json(response)
```

## License

MIT
