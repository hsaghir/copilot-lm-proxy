"""Tests for module-level async convenience functions (task 1.3)."""

from __future__ import annotations

import asyncio
import http.server
import json
import threading
from typing import Generator
from unittest.mock import patch

import pytest

import copilot_proxy
from copilot_proxy import (
    AsyncCopilotClient,
    async_ask,
    async_chat,
    async_list_models,
)
from copilot_proxy.client import _get_async_client


# ---------------------------------------------------------------------------
# Minimal mock server
# ---------------------------------------------------------------------------

MOCK_MODELS = [
    {"id": "gpt-4.1", "family": "gpt-4.1", "vendor": "copilot", "version": "gpt-4.1-2025-04-14", "maxInputTokens": 111424},
    {"id": "claude-sonnet-4", "family": "claude-sonnet-4", "vendor": "copilot", "version": "claude-sonnet-4", "maxInputTokens": 127805},
]


class MockProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

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
        if self.path == "/v1/chat/completions":
            data = self._read_body()
            messages = data.get("messages", [])
            stream = data.get("stream", False)
            last_msg = messages[-1]["content"] if messages else ""
            reply = f"Mock response to: {last_msg}"
            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                for word in reply.split():
                    chunk = json.dumps({"choices": [{"delta": {"content": word + " "}}]})
                    self.wfile.write(f"data: {chunk}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self._send_json({
                    "model": "gpt-4.1",
                    "choices": [{"message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                })
        else:
            self._send_json({"error": "Not found"}, 404)


@pytest.fixture(scope="module")
def mock_server() -> Generator[str, None, None]:
    server = http.server.HTTPServer(("127.0.0.1", 0), MockProxyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests: exports and __all__
# ---------------------------------------------------------------------------

class TestExports:
    def test_async_copilot_client_in_all(self) -> None:
        assert "AsyncCopilotClient" in copilot_proxy.__all__

    def test_async_ask_in_all(self) -> None:
        assert "async_ask" in copilot_proxy.__all__

    def test_async_chat_in_all(self) -> None:
        assert "async_chat" in copilot_proxy.__all__

    def test_async_list_models_in_all(self) -> None:
        assert "async_list_models" in copilot_proxy.__all__

    def test_import_async_ask(self) -> None:
        assert callable(async_ask)

    def test_import_async_chat(self) -> None:
        assert callable(async_chat)

    def test_import_async_list_models(self) -> None:
        assert callable(async_list_models)

    def test_version_is_0_3_0(self) -> None:
        assert copilot_proxy.__version__ == "0.3.0"


# ---------------------------------------------------------------------------
# Tests: _get_async_client singleton
# ---------------------------------------------------------------------------

class TestGetAsyncClient:
    def test_returns_async_copilot_client(self) -> None:
        client = _get_async_client()
        assert isinstance(client, AsyncCopilotClient)

    def test_singleton_same_instance(self) -> None:
        c1 = _get_async_client()
        c2 = _get_async_client()
        assert c1 is c2


# ---------------------------------------------------------------------------
# Tests: module-level async functions with patched client
# ---------------------------------------------------------------------------

class TestAsyncModuleFunctions:
    def test_async_ask_returns_string(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = asyncio.run(async_ask("Hello from module"))
        assert isinstance(result, str)
        assert "Hello" in result

    def test_async_ask_with_model(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = asyncio.run(async_ask("Test", model="gpt-4.1"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_async_chat_returns_string(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = asyncio.run(async_chat([{"role": "user", "content": "Module chat"}]))
        assert isinstance(result, str)

    def test_async_chat_streaming(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def collect():
            parts = []
            async for chunk in await async_chat(
                [{"role": "user", "content": "Stream test"}], stream=True
            ):
                parts.append(chunk)
            return "".join(parts)

        with patch("copilot_proxy.client._default_async_client", patched):
            result = asyncio.run(collect())
        assert len(result) > 0

    def test_async_list_models_returns_list(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            models = asyncio.run(async_list_models())
        assert isinstance(models, list)
        assert len(models) == 2

    def test_async_list_models_fields(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            models = asyncio.run(async_list_models())
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m
