"""Basic tests for AsyncCopilotClient (task 1.1).

Uses asyncio.run() wrappers so these work without pytest-asyncio.
Full async test coverage (with pytest-asyncio) is in task 2.2.
"""

from __future__ import annotations

import asyncio
import http.server
import json
import threading
from typing import Generator

import pytest

from copilot_proxy import AsyncCopilotClient


# ---------------------------------------------------------------------------
# Minimal mock server (mirrors test_client.py's MockProxyHandler)
# ---------------------------------------------------------------------------

MOCK_MODELS = [
    {"id": "gpt-4.1", "family": "gpt-4.1", "vendor": "copilot", "version": "gpt-4.1-2025-04-14", "maxInputTokens": 111424},
    {"id": "claude-sonnet-4", "family": "claude-sonnet-4", "vendor": "copilot", "version": "claude-sonnet-4", "maxInputTokens": 127805},
]


class MockProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

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


@pytest.fixture(scope="module")
def mock_server() -> Generator[str, None, None]:
    server = http.server.HTTPServer(("127.0.0.1", 0), MockProxyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAsyncCopilotClientInstantiation:
    def test_default_constructor(self) -> None:
        client = AsyncCopilotClient()
        assert client.base_url.startswith("http")
        assert client.timeout == 120

    def test_custom_base_url(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:9999")
        assert client.base_url == "http://127.0.0.1:9999"

    def test_custom_timeout(self) -> None:
        client = AsyncCopilotClient(timeout=30)
        assert client.timeout == 30

    def test_trailing_slash_stripped(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:9999/")
        assert not client.base_url.endswith("/")

    def test_custom_base_url_and_timeout(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:5000", timeout=60)
        assert client.base_url == "http://127.0.0.1:5000"
        assert client.timeout == 60


class TestAsyncIsRunning:
    def test_is_running_true(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.is_running())
        assert result is True

    def test_is_running_false_bad_port(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        result = asyncio.run(client.is_running())
        assert result is False

    def test_is_running_does_not_raise(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        # Should return bool, not raise
        result = asyncio.run(client.is_running())
        assert isinstance(result, bool)


class TestAsyncListModels:
    def test_list_models_returns_list(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        models = asyncio.run(client.list_models())
        assert isinstance(models, list)
        assert len(models) > 0

    def test_list_models_has_expected_fields(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        models = asyncio.run(client.list_models())
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m

    def test_list_models_correct_count(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        models = asyncio.run(client.list_models())
        assert len(models) == 2

    def test_list_models_ids(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        models = asyncio.run(client.list_models())
        ids = {m["id"] for m in models}
        assert "gpt-4.1" in ids
        assert "claude-sonnet-4" in ids
