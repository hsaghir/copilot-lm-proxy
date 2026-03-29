"""Tests for AsyncCopilotClient.chat() and AsyncCopilotClient.ask() (task 1.2).

Uses asyncio.run() wrappers so these work without pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import http.server
import json
import threading
from typing import Generator

import pytest

from copilot_proxy.client import AsyncCopilotClient, ModelNotFoundError, ProxyConnectionError


# ---------------------------------------------------------------------------
# Minimal mock server (mirrors the one in test_client.py)
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
            model = data.get("model", "gpt-4.1")
            messages = data.get("messages", [])
            stream = data.get("stream", False)

            if model == "nonexistent-model":
                self._send_json({"error": "No models available. Is Copilot signed in?"}, 404)
                return

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
                    "model": model,
                    "choices": [{
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }],
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
# Tests: async chat (non-streaming)
# ---------------------------------------------------------------------------

class TestAsyncChatNonStreaming:
    def test_chat_returns_string(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.chat([{"role": "user", "content": "Hello"}]))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_echoes_prompt(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.chat([{"role": "user", "content": "Hello"}]))
        assert "Hello" in result

    def test_chat_with_model(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.chat([{"role": "user", "content": "Test"}], model="gpt-4.1"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_multi_turn(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is Python?"},
        ]
        result = asyncio.run(client.chat(messages))
        assert isinstance(result, str)
        assert "Python" in result

    def test_chat_model_not_found(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with pytest.raises(ModelNotFoundError):
            asyncio.run(client.chat([{"role": "user", "content": "Hi"}], model="nonexistent-model"))

    def test_chat_connection_error(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError):
            asyncio.run(client.chat([{"role": "user", "content": "Hi"}]))


# ---------------------------------------------------------------------------
# Tests: async chat (streaming)
# ---------------------------------------------------------------------------

class TestAsyncChatStreaming:
    def test_stream_yields_chunks(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def collect():
            chunks = []
            async for chunk in await client.chat(
                [{"role": "user", "content": "Hello world"}], stream=True
            ):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(collect())
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    def test_stream_chunks_concatenate_to_valid_response(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def collect():
            parts = []
            async for chunk in await client.chat(
                [{"role": "user", "content": "Hello world"}], stream=True
            ):
                parts.append(chunk)
            return "".join(parts)

        full = asyncio.run(collect())
        assert "Hello" in full
        assert "world" in full

    def test_stream_with_model(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def collect():
            parts = []
            async for chunk in await client.chat(
                [{"role": "user", "content": "Test"}],
                model="claude-sonnet-4",
                stream=True,
            ):
                parts.append(chunk)
            return "".join(parts)

        full = asyncio.run(collect())
        assert len(full) > 0

    def test_stream_early_break_no_dangling_resources(self, mock_server: str) -> None:
        """Breaking out of the async for loop should not leave dangling threads."""
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def break_early():
            async for _chunk in await client.chat(
                [{"role": "user", "content": "Hello world streaming test"}], stream=True
            ):
                break  # break after first chunk

        # Should complete without hanging or raising
        asyncio.run(asyncio.wait_for(break_early(), timeout=5.0))

    def test_stream_connection_error(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)

        async def try_stream():
            async for _chunk in await client.chat(
                [{"role": "user", "content": "Hi"}], stream=True
            ):
                pass

        with pytest.raises(ProxyConnectionError):
            asyncio.run(try_stream())


# ---------------------------------------------------------------------------
# Tests: async ask
# ---------------------------------------------------------------------------

class TestAsyncAsk:
    def test_ask_returns_string(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.ask("Hello"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ask_echoes_prompt(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.ask("Hello"))
        assert "Hello" in result

    def test_ask_with_model(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.ask("Test", model="gpt-4.1"))
        assert isinstance(result, str)

    def test_ask_equivalent_to_chat(self, mock_server: str) -> None:
        """ask(prompt) should be equivalent to chat([{role:user, content:prompt}])."""
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)

        async def compare():
            via_ask = await client.ask("Hello compare")
            via_chat = await client.chat([{"role": "user", "content": "Hello compare"}])
            return via_ask, via_chat

        ask_result, chat_result = asyncio.run(compare())
        assert ask_result == chat_result

    def test_ask_unicode(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.ask("Bonjour 🌍"))
        assert isinstance(result, str)

    def test_ask_long_prompt(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        result = asyncio.run(client.ask("x" * 5000))
        assert isinstance(result, str)

    def test_ask_model_not_found(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with pytest.raises(ModelNotFoundError):
            asyncio.run(client.ask("Hi", model="nonexistent-model"))

    def test_ask_connection_error(self) -> None:
        client = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError):
            asyncio.run(client.ask("Hi"))
