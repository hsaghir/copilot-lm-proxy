"""Tests for copilot_proxy.client using a real local HTTP mock server."""

from __future__ import annotations

import asyncio
import urllib.error
from typing import Generator
from unittest.mock import patch

import pytest

from copilot_proxy import (
    AsyncCopilotClient,
    CopilotClient,
    CopilotProxyError,
    ModelNotFoundError,
    ProxyConnectionError,
    ask,
    chat,
    list_models,
)


@pytest.fixture
def client(mock_server: str) -> CopilotClient:
    """Create a CopilotClient pointing at the mock server."""
    return CopilotClient(base_url=mock_server, timeout=10)


# ---------------------------------------------------------------------------
# Tests: CopilotClient
# ---------------------------------------------------------------------------

class TestCopilotClient:
    def test_list_models(self, client: CopilotClient) -> None:
        models = client.list_models()
        assert isinstance(models, list)
        assert len(models) == 2
        ids = {m["id"] for m in models}
        assert "gpt-4.1" in ids
        assert "claude-sonnet-4" in ids

    def test_list_models_has_expected_fields(self, client: CopilotClient) -> None:
        models = client.list_models()
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m

    def test_ask_returns_string(self, client: CopilotClient) -> None:
        result = client.ask("Hello")
        assert isinstance(result, str)
        assert "Hello" in result  # mock echoes prompt

    def test_ask_with_model(self, client: CopilotClient) -> None:
        result = client.ask("Test", model="gpt-4.1")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_single_message(self, client: CopilotClient) -> None:
        result = client.chat([{"role": "user", "content": "Hi"}])
        assert isinstance(result, str)
        assert "Hi" in result

    def test_chat_multi_turn(self, client: CopilotClient) -> None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is Python?"},
        ]
        result = client.chat(messages)
        assert isinstance(result, str)
        assert "Python" in result

    def test_chat_stream(self, client: CopilotClient) -> None:
        result = client.chat(
            [{"role": "user", "content": "Hello world"}],
            stream=True,
        )
        chunks = list(result)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert "Hello" in full

    def test_chat_stream_with_model(self, client: CopilotClient) -> None:
        result = client.chat(
            [{"role": "user", "content": "Test"}],
            model="claude-sonnet-4",
            stream=True,
        )
        full = "".join(result)
        assert len(full) > 0

    def test_model_not_found(self, client: CopilotClient) -> None:
        with pytest.raises(ModelNotFoundError):
            client.ask("Hello", model="nonexistent-model")

    def test_connection_error_bad_port(self) -> None:
        bad_client = CopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError, match="Cannot connect"):
            bad_client.list_models()

    def test_connection_error_is_copilot_proxy_error(self) -> None:
        """ProxyConnectionError should be a subclass of CopilotProxyError."""
        assert issubclass(ProxyConnectionError, CopilotProxyError)

    def test_model_not_found_is_copilot_proxy_error(self) -> None:
        assert issubclass(ModelNotFoundError, CopilotProxyError)

    def test_base_url_trailing_slash(self, mock_server: str) -> None:
        c = CopilotClient(base_url=mock_server + "/", timeout=10)
        models = c.list_models()
        assert len(models) > 0

    def test_custom_timeout(self, mock_server: str) -> None:
        c = CopilotClient(base_url=mock_server, timeout=5)
        assert c.timeout == 5
        # Should still work
        result = c.ask("Quick test")
        assert isinstance(result, str)

    def test_is_running_true(self, client: CopilotClient) -> None:
        assert client.is_running() is True

    def test_is_running_false(self) -> None:
        bad_client = CopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        assert bad_client.is_running() is False


# ---------------------------------------------------------------------------
# Tests: Module-level convenience functions
# ---------------------------------------------------------------------------

class TestModuleFunctions:
    """Test the module-level ask/chat/list_models functions."""

    def test_ask_function(self, mock_server: str) -> None:
        with patch("copilot_proxy.client._default_client", CopilotClient(mock_server, timeout=10)):
            result = ask("Hello from module")
            assert isinstance(result, str)
            assert "Hello" in result

    def test_chat_function(self, mock_server: str) -> None:
        with patch("copilot_proxy.client._default_client", CopilotClient(mock_server, timeout=10)):
            result = chat([{"role": "user", "content": "Module chat"}])
            assert isinstance(result, str)

    def test_list_models_function(self, mock_server: str) -> None:
        with patch("copilot_proxy.client._default_client", CopilotClient(mock_server, timeout=10)):
            models = list_models()
            assert isinstance(models, list)
            assert len(models) == 2


# ---------------------------------------------------------------------------
# Tests: Edge cases and robustness
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_message_list(self, client: CopilotClient) -> None:
        # Server should handle empty messages gracefully
        result = client.chat([])
        assert isinstance(result, str)

    def test_long_prompt(self, client: CopilotClient) -> None:
        long_prompt = "x" * 10000
        result = client.ask(long_prompt)
        assert isinstance(result, str)

    def test_special_characters_in_prompt(self, client: CopilotClient) -> None:
        result = client.ask('Hello "world" <script>alert(1)</script> \n\t')
        assert isinstance(result, str)

    def test_unicode_prompt(self, client: CopilotClient) -> None:
        result = client.ask("Explique les réseaux neuronaux 🧠")
        assert isinstance(result, str)

    def test_stream_empty_deltas(self, client: CopilotClient) -> None:
        """Streaming should handle chunks without content gracefully."""
        result = client.chat(
            [{"role": "user", "content": "Test"}],
            stream=True,
        )
        # Should not raise; just iterate
        chunks = list(result)
        assert isinstance(chunks, list)


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient
# ---------------------------------------------------------------------------

@pytest.fixture
def async_client(mock_server: str) -> AsyncCopilotClient:
    """Create an AsyncCopilotClient pointing at the mock server."""
    return AsyncCopilotClient(base_url=mock_server, timeout=10)


class TestAsyncCopilotClient:
    """Tests for AsyncCopilotClient — basic instantiation and async methods."""

    def test_instantiation_defaults(self) -> None:
        c = AsyncCopilotClient()
        assert c.base_url.startswith("http")
        assert c.timeout == 120

    def test_instantiation_custom(self, mock_server: str) -> None:
        c = AsyncCopilotClient(base_url=mock_server, timeout=5)
        assert c.base_url == mock_server.rstrip("/")
        assert c.timeout == 5

    def test_instantiation_trailing_slash(self, mock_server: str) -> None:
        c = AsyncCopilotClient(base_url=mock_server + "/", timeout=10)
        assert not c.base_url.endswith("/")

    def test_is_running_true(self, async_client: AsyncCopilotClient) -> None:
        result = asyncio.run(async_client.is_running())
        assert result is True

    def test_is_running_false(self) -> None:
        bad = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        result = asyncio.run(bad.is_running())
        assert result is False

    def test_list_models_returns_list(self, async_client: AsyncCopilotClient) -> None:
        models = asyncio.run(async_client.list_models())
        assert isinstance(models, list)
        assert len(models) > 0

    def test_list_models_has_required_keys(self, async_client: AsyncCopilotClient) -> None:
        models = asyncio.run(async_client.list_models())
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m

    def test_is_coroutine(self, async_client: AsyncCopilotClient) -> None:
        """is_running() and list_models() must return awaitables."""
        import inspect
        coro1 = async_client.is_running()
        coro2 = async_client.list_models()
        assert inspect.iscoroutine(coro1)
        assert inspect.iscoroutine(coro2)
        coro1.close()
        coro2.close()


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.chat and .ask (task 1.2)
# ---------------------------------------------------------------------------

class TestAsyncCopilotClientChat:
    """Tests for AsyncCopilotClient.chat() and .ask()."""

    def test_chat_non_streaming_returns_string(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.chat([{"role": "user", "content": "Hello"}])
        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_non_streaming_echoes_content(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.chat([{"role": "user", "content": "async test"}])
        result = asyncio.run(run())
        assert "async test" in result

    def test_chat_with_model(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.chat(
                [{"role": "user", "content": "Hi"}],
                model="gpt-4.1",
            )
        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_streaming_yields_chunks(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            chunks = []
            async for chunk in await async_client.chat(
                [{"role": "user", "content": "Hello world"}],
                stream=True,
            ):
                chunks.append(chunk)
            return chunks
        chunks = asyncio.run(run())
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        full = "".join(chunks)
        assert "Hello" in full

    def test_chat_streaming_concatenates_to_valid_response(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            parts = []
            async for chunk in await async_client.chat(
                [{"role": "user", "content": "stream test"}],
                stream=True,
            ):
                parts.append(chunk)
            return "".join(parts)
        full = asyncio.run(run())
        assert len(full) > 0
        assert "stream" in full

    def test_chat_streaming_with_model(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            parts = []
            async for chunk in await async_client.chat(
                [{"role": "user", "content": "model stream"}],
                model="claude-sonnet-4",
                stream=True,
            ):
                parts.append(chunk)
            return parts
        chunks = asyncio.run(run())
        assert len(chunks) > 0

    def test_chat_streaming_break_no_hang(self, async_client: AsyncCopilotClient) -> None:
        """Breaking out of the async generator should not hang or raise."""
        async def run():
            first = None
            async for chunk in await async_client.chat(
                [{"role": "user", "content": "break test"}],
                stream=True,
            ):
                first = chunk
                break  # cancel early
            return first
        result = asyncio.run(run())
        assert result is not None

    def test_ask_returns_string(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.ask("What is Python?")
        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ask_echoes_prompt(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.ask("my unique prompt text")
        result = asyncio.run(run())
        assert "my unique prompt text" in result

    def test_ask_with_model(self, async_client: AsyncCopilotClient) -> None:
        async def run():
            return await async_client.ask("Hello", model="gpt-4.1")
        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ask_equivalent_to_chat(self, async_client: AsyncCopilotClient) -> None:
        """ask(prompt) should match chat([{role:user, content:prompt}])."""
        async def run():
            r1 = await async_client.ask("equivalence check")
            r2 = await async_client.chat([{"role": "user", "content": "equivalence check"}])
            return r1, r2
        r1, r2 = asyncio.run(run())
        assert r1 == r2

    def test_chat_model_not_found(self, async_client: AsyncCopilotClient) -> None:
        from copilot_proxy import ModelNotFoundError
        async def run():
            await async_client.chat(
                [{"role": "user", "content": "hi"}],
                model="nonexistent-model",
            )
        with pytest.raises(ModelNotFoundError):
            asyncio.run(run())
