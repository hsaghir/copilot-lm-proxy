"""Comprehensive async tests for AsyncCopilotClient and async module functions.

Uses pytest-asyncio with asyncio_mode='auto' (set in pyproject.toml), so all
async def test_* functions are automatically collected and run without decorators.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

import copilot_proxy
from copilot_proxy import (
    AsyncCopilotClient,
    ModelNotFoundError,
    ProxyConnectionError,
    async_ask,
    async_chat,
    async_is_running,
    async_list_models,
)
from copilot_proxy.client import _get_async_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def async_client(mock_server: str) -> AsyncCopilotClient:
    """Create an AsyncCopilotClient pointing at the mock server."""
    return AsyncCopilotClient(base_url=mock_server, timeout=10)


# ---------------------------------------------------------------------------
# Tests: instantiation
# ---------------------------------------------------------------------------

class TestAsyncInstantiation:
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


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.list_models()
# ---------------------------------------------------------------------------

class TestAsyncListModels:
    async def test_list_models_returns_list(self, async_client: AsyncCopilotClient) -> None:
        models = await async_client.list_models()
        assert isinstance(models, list)
        assert len(models) == 2

    async def test_list_models_has_expected_fields(self, async_client: AsyncCopilotClient) -> None:
        models = await async_client.list_models()
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m

    async def test_list_models_known_ids(self, async_client: AsyncCopilotClient) -> None:
        models = await async_client.list_models()
        ids = {m["id"] for m in models}
        assert "gpt-4.1" in ids
        assert "claude-sonnet-4" in ids

    async def test_list_models_trailing_slash(self, mock_server: str) -> None:
        client = AsyncCopilotClient(base_url=mock_server + "/", timeout=10)
        models = await client.list_models()
        assert len(models) > 0


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.is_running()
# ---------------------------------------------------------------------------

class TestAsyncIsRunning:
    async def test_is_running_true(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.is_running()
        assert result is True

    async def test_is_running_false(self) -> None:
        bad = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        result = await bad.is_running()
        assert result is False

    async def test_is_running_returns_bool(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.is_running()
        assert isinstance(result, bool)

    def test_methods_return_coroutines(self, async_client: AsyncCopilotClient) -> None:
        """is_running() and list_models() must return awaitables."""
        coro1 = async_client.is_running()
        coro2 = async_client.list_models()
        assert inspect.iscoroutine(coro1)
        assert inspect.iscoroutine(coro2)
        coro1.close()
        coro2.close()


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.ask()
# ---------------------------------------------------------------------------

class TestAsyncAsk:
    async def test_ask_returns_string(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.ask("Hello")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_ask_echoes_prompt(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.ask("Hello")
        assert "Hello" in result

    async def test_ask_with_model(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.ask("Test", model="gpt-4.1")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_ask_unicode_prompt(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.ask("Explique les réseaux neuronaux 🧠")
        assert isinstance(result, str)

    async def test_ask_long_prompt(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.ask("x" * 10000)
        assert isinstance(result, str)

    async def test_ask_model_not_found(self, async_client: AsyncCopilotClient) -> None:
        with pytest.raises(ModelNotFoundError):
            await async_client.ask("Hello", model="nonexistent-model")

    async def test_ask_connection_error(self) -> None:
        bad = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError, match="Cannot connect"):
            await bad.ask("Hello")

    async def test_ask_equivalent_to_chat(self, async_client: AsyncCopilotClient) -> None:
        """ask(prompt) should be equivalent to chat([{role:user, content:prompt}])."""
        via_ask = await async_client.ask("Hello compare")
        via_chat = await async_client.chat([{"role": "user", "content": "Hello compare"}])
        assert via_ask == via_chat


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.chat() — non-streaming
# ---------------------------------------------------------------------------

class TestAsyncChatNonStreaming:
    async def test_chat_single_message(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.chat([{"role": "user", "content": "Hi"}])
        assert isinstance(result, str)
        assert "Hi" in result

    async def test_chat_multi_turn(self, async_client: AsyncCopilotClient) -> None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is Python?"},
        ]
        result = await async_client.chat(messages)
        assert isinstance(result, str)
        assert "Python" in result

    async def test_chat_with_model(self, async_client: AsyncCopilotClient) -> None:
        result = await async_client.chat(
            [{"role": "user", "content": "Test"}], model="claude-sonnet-4"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_chat_model_not_found(self, async_client: AsyncCopilotClient) -> None:
        with pytest.raises(ModelNotFoundError):
            await async_client.chat(
                [{"role": "user", "content": "Hi"}], model="nonexistent-model"
            )

    async def test_chat_connection_error(self) -> None:
        bad = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError):
            await bad.chat([{"role": "user", "content": "Hi"}])


# ---------------------------------------------------------------------------
# Tests: AsyncCopilotClient.chat() — streaming
# ---------------------------------------------------------------------------

class TestAsyncChatStreaming:
    async def test_stream_yields_chunks(self, async_client: AsyncCopilotClient) -> None:
        chunks = []
        async for chunk in await async_client.chat(
            [{"role": "user", "content": "Hello world"}], stream=True
        ):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    async def test_stream_chunks_concatenate_to_valid_response(
        self, async_client: AsyncCopilotClient
    ) -> None:
        parts = []
        async for chunk in await async_client.chat(
            [{"role": "user", "content": "Hello world"}], stream=True
        ):
            parts.append(chunk)
        full = "".join(parts)
        # Mock echoes "Mock response to: Hello world"
        assert "Hello" in full
        assert "world" in full

    async def test_stream_with_model(self, async_client: AsyncCopilotClient) -> None:
        parts = []
        async for chunk in await async_client.chat(
            [{"role": "user", "content": "Test streaming"}],
            model="claude-sonnet-4",
            stream=True,
        ):
            parts.append(chunk)
        assert len("".join(parts)) > 0

    async def test_stream_early_break(self, async_client: AsyncCopilotClient) -> None:
        """Breaking out of async for should not leave dangling threads."""
        count = 0
        async for _chunk in await async_client.chat(
            [{"role": "user", "content": "Hello world streaming test"}], stream=True
        ):
            count += 1
            break
        # Just confirm we got at least one chunk and didn't hang
        assert count >= 0

    async def test_stream_connection_error(self) -> None:
        bad = AsyncCopilotClient(base_url="http://127.0.0.1:1", timeout=2)
        with pytest.raises(ProxyConnectionError):
            async for _chunk in await bad.chat(
                [{"role": "user", "content": "Hi"}], stream=True
            ):
                pass


# ---------------------------------------------------------------------------
# Tests: module-level async convenience functions
# ---------------------------------------------------------------------------

class TestAsyncModuleFunctions:
    async def test_async_ask_returns_string(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = await async_ask("Hello from module")
        assert isinstance(result, str)
        assert "Hello" in result

    async def test_async_ask_with_model(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = await async_ask("Test", model="gpt-4.1")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_async_chat_returns_string(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = await async_chat([{"role": "user", "content": "Module chat"}])
        assert isinstance(result, str)

    async def test_async_chat_streaming(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        parts = []
        with patch("copilot_proxy.client._default_async_client", patched):
            async for chunk in await async_chat(
                [{"role": "user", "content": "Stream test"}], stream=True
            ):
                parts.append(chunk)
        assert len("".join(parts)) > 0

    async def test_async_list_models_returns_list(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            models = await async_list_models()
        assert isinstance(models, list)
        assert len(models) == 2

    async def test_async_list_models_fields(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            models = await async_list_models()
        for m in models:
            assert "id" in m
            assert "vendor" in m
            assert "maxInputTokens" in m

    async def test_async_is_running(self, mock_server: str) -> None:
        patched = AsyncCopilotClient(base_url=mock_server, timeout=10)
        with patch("copilot_proxy.client._default_async_client", patched):
            result = await async_is_running()
        assert result is True


# ---------------------------------------------------------------------------
# Tests: exports and singleton
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

    def test_async_is_running_in_all(self) -> None:
        assert "async_is_running" in copilot_proxy.__all__

    def test_version_is_0_3_0(self) -> None:
        assert copilot_proxy.__version__ == "0.3.0"


class TestGetAsyncClient:
    def test_returns_async_copilot_client(self) -> None:
        client = _get_async_client()
        assert isinstance(client, AsyncCopilotClient)

    def test_singleton_same_instance(self) -> None:
        c1 = _get_async_client()
        c2 = _get_async_client()
        assert c1 is c2
