"""Shared test fixtures for copilot_proxy tests."""

from __future__ import annotations

import http.server
import json
import threading
from typing import Generator

import pytest


# ---------------------------------------------------------------------------
# Mock proxy server: shared by test_client.py and test_async_client.py
# ---------------------------------------------------------------------------

MOCK_MODELS = [
    {"id": "gpt-4.1", "family": "gpt-4.1", "vendor": "copilot", "version": "gpt-4.1-2025-04-14", "maxInputTokens": 111424},
    {"id": "claude-sonnet-4", "family": "claude-sonnet-4", "vendor": "copilot", "version": "claude-sonnet-4", "maxInputTokens": 127805},
]


class MockProxyHandler(http.server.BaseHTTPRequestHandler):
    """Minimal handler that behaves like the VS Code extension proxy."""

    def log_message(self, format: str, *args: object) -> None:
        pass  # suppress logs during tests

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json({"object": "list", "data": MOCK_MODELS, "models": MOCK_MODELS})
        elif self.path == "/health":
            self._send_json({"status": "ok", "pid": 12345})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/v1/models":
            self._send_json({"object": "list", "data": MOCK_MODELS, "models": MOCK_MODELS})

        elif self.path == "/v1/chat/completions":
            data = self._read_body()
            model = data.get("model", "gpt-4.1")
            messages = data.get("messages", [])
            stream = data.get("stream", False)

            # Simulate model-not-found
            if model == "nonexistent-model":
                self._send_json({"error": "No models available. Is Copilot signed in?"}, 404)
                return

            # Build a deterministic response from the last user message
            last_msg = messages[-1]["content"] if messages else ""
            reply = f"Mock response to: {last_msg}"

            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                # Send reply word-by-word as SSE chunks
                for word in reply.split():
                    chunk = json.dumps({"choices": [{"delta": {"content": word + " "}}]})
                    self.wfile.write(f"data: {chunk}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self._send_json({
                    "model": model,
                    "choices": [{
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }],
                })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()


@pytest.fixture(scope="module")
def mock_server() -> Generator[str, None, None]:
    """Start a mock proxy server and yield its base URL."""
    server = http.server.HTTPServer(("127.0.0.1", 0), MockProxyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
