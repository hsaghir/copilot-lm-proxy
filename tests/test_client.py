"""Tests for copilot_proxy.client using a real local HTTP mock server."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from copilot_proxy import (
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
