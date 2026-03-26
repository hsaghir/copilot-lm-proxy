"""
Python client for Copilot Proxy extension.

Usage:
    1. Install the VS Code extension (see scratch/copilot-proxy-extension/)
    2. Run: uv run scratch/copilot_proxy_client.py
"""

import json
import urllib.request

from pydantic import BaseModel

PROXY_URL = "http://127.0.0.1:19823"


def list_models() -> list[dict]:
    """List available Copilot models."""
    req = urllib.request.Request(f"{PROXY_URL}/v1/models", method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["models"]


def chat(messages: list[dict], model: str | None = None, stream: bool = False) -> str:
    """Send chat completion request to Copilot via proxy."""
    payload = {"messages": messages, "stream": stream}
    if model:
        payload["model"] = model

    req = urllib.request.Request(
        f"{PROXY_URL}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def ask(prompt: str, model: str | None = None) -> str:
    """Simple helper to ask a single question."""
    return chat([{"role": "user", "content": prompt}], model=model)


def ask_claude(prompt: str) -> str:
    """Ask Claude Opus 4.5 specifically."""
    return ask(prompt, model="claude-opus-4.5")


# Pydantic model for structured output test
class NeuralNetExplanation(BaseModel):
    title: str
    summary: str
    key_concepts: list[str]
    difficulty_level: str


if __name__ == "__main__":
    print("=" * 60)
    print("Copilot Proxy Client")
    print("=" * 60)

    # Check if proxy is running
    try:
        models = list_models()
        print("\n✅ Connected! Available models:")
        for m in models:
            print(f"   - {m['id']} ({m['family']}, {m['vendor']})")
    except Exception as e:
        print(f"\n❌ Could not connect to proxy: {e}")
        print("\nMake sure the Copilot Proxy extension is installed and running:")
        print("  1. cd scratch/copilot-proxy-extension")
        print("  2. npm install && npm run compile")
        print("  3. Press F5 in VS Code to launch Extension Development Host")
        print(
            "  4. Or package with: npx vsce package && code --install-extension copilot-proxy-0.0.1.vsix"
        )
        exit(1)

    # Test 1: Simple prompt
    print("\n" + "=" * 60)
    print("Test 1: Simple prompt")
    print("=" * 60)
    response = ask("Hey, explain neural nets in 2-3 sentences.")
    print(response)

    # Test 2: Structured output
    print("\n" + "=" * 60)
    print("Test 2: Structured output with Pydantic")
    print("=" * 60)
    schema = NeuralNetExplanation.model_json_schema()
    prompt = f"""Explain neural networks. Return ONLY valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Return ONLY the JSON object, no markdown or explanation."""

    response = ask(prompt)
    print(f"Raw: {response}\n")

    # Strip markdown if present
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]

    parsed = NeuralNetExplanation.model_validate_json(response)
    print("Parsed Pydantic object:")
    print(f"  Title: {parsed.title}")
    print(f"  Summary: {parsed.summary}")
    print(f"  Key concepts: {parsed.key_concepts}")
    print(f"  Difficulty: {parsed.difficulty_level}")
