"""Integration tests against the real Copilot Proxy server.

These tests only run when the proxy is actually running on port 19823.
Skip them in CI or when the extension isn't active.

Run with: pytest tests/test_integration.py -v
"""

from __future__ import annotations

import pytest

from copilot_proxy import CopilotClient, is_running

PROXY_URL = "http://127.0.0.1:19823"


pytestmark = pytest.mark.skipif(
    not is_running(),
    reason="Copilot Proxy not running on port 19823",
)


@pytest.fixture
def client() -> CopilotClient:
    return CopilotClient(base_url=PROXY_URL, timeout=60)


class TestIntegration:
    def test_list_models(self, client: CopilotClient) -> None:
        models = client.list_models()
        assert len(models) > 0
        assert all("id" in m for m in models)

    def test_ask_simple(self, client: CopilotClient) -> None:
        result = client.ask("What is 2+2? Reply with just the number.")
        assert "4" in result

    def test_ask_with_model(self, client: CopilotClient) -> None:
        result = client.ask("Say 'hello' and nothing else.", model="gpt-4o")
        assert "hello" in result.lower()

    def test_chat_multi_turn(self, client: CopilotClient) -> None:
        result = client.chat([
            {"role": "system", "content": "You are a calculator. Only output numbers."},
            {"role": "user", "content": "What is 3+3?"},
        ])
        assert "6" in result

    def test_stream(self, client: CopilotClient) -> None:
        result = client.chat(
            [{"role": "user", "content": "Say 'test' and nothing else."}],
            stream=True,
        )
        chunks = list(result)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert "test" in full.lower()
