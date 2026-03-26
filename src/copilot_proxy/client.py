"""Copilot Proxy client implementation."""

from __future__ import annotations

import json
import urllib.request
from typing import Iterator

DEFAULT_URL = "http://127.0.0.1:19823"


class CopilotClient:
    """Client for the Copilot Proxy server."""

    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_models(self) -> list[dict]:
        """List available Copilot models."""
        req = urllib.request.Request(f"{self.base_url}/v1/models", method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())["models"]

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Send chat completion request."""
        payload: dict = {"messages": messages, "stream": stream}
        if model:
            payload["model"] = model

        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

        if stream:
            return self._stream_response(req)
        else:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"]

    def _stream_response(self, req: urllib.request.Request) -> Iterator[str]:
        """Stream response chunks."""
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for line in resp:
                line = line.decode().strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    if "choices" in data and data["choices"]:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    def ask(self, prompt: str, model: str | None = None) -> str:
        """Simple helper to ask a single question."""
        result = self.chat([{"role": "user", "content": prompt}], model=model)
        if isinstance(result, str):
            return result
        return "".join(result)


_default_client: CopilotClient | None = None


def _get_client() -> CopilotClient:
    global _default_client
    if _default_client is None:
        _default_client = CopilotClient()
    return _default_client


def list_models() -> list[dict]:
    """List available Copilot models."""
    return _get_client().list_models()


def chat(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
) -> str | Iterator[str]:
    """Send chat completion request to Copilot via proxy."""
    return _get_client().chat(messages, model=model, stream=stream)


def ask(prompt: str, model: str | None = None) -> str:
    """Simple helper to ask a single question."""
    return _get_client().ask(prompt, model=model)
