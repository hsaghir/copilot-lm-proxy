"""Copilot Proxy client implementation."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

DEFAULT_URL = os.environ.get("COPILOT_PROXY_URL", "http://127.0.0.1:19823")


class CopilotProxyError(Exception):
    """Base exception for Copilot Proxy errors."""


class ProxyConnectionError(CopilotProxyError):
    """Raised when the proxy server is unreachable."""


class ModelNotFoundError(CopilotProxyError):
    """Raised when the requested model is not available."""


class CopilotClient:
    """Client for the Copilot Proxy server.

    Args:
        base_url: URL of the proxy server (default: http://127.0.0.1:19823).
        timeout: Request timeout in seconds (default: 120).
    """

    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, data: dict | None = None, method: str = "GET") -> dict:
        """Make an HTTP request to the proxy server.

        Returns the parsed JSON response.
        Raises CopilotProxyError subclasses on failure.
        """
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        if body:
            method = "POST"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            if isinstance(e, urllib.error.HTTPError):
                try:
                    err_body = json.loads(e.read())
                    msg = err_body.get("error", str(e))
                except Exception:
                    msg = str(e)
                if e.code == 404:
                    raise ModelNotFoundError(msg) from e
                raise CopilotProxyError(msg) from e
            raise ProxyConnectionError(
                f"Cannot connect to Copilot Proxy at {self.base_url}. "
                "Is the VS Code extension running? Try reloading VS Code."
            ) from e

    def is_running(self) -> bool:
        """Check if the proxy server is running and healthy."""
        try:
            result = self._request("/health")
            return result.get("status") == "ok"
        except CopilotProxyError:
            return False

    def list_models(self) -> list[dict]:
        """List available Copilot models.

        Returns:
            List of model dicts with keys: id, family, vendor, version, maxInputTokens.

        Raises:
            ConnectionError: If the proxy server is unreachable.
        """
        result = self._request("/v1/models")
        # Support both our format {"models": [...]} and OpenAI format {"data": [...]}
        return result.get("models") or result.get("data", [])

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model ID to use (e.g. 'gpt-4.1'). None for default.
            stream: If True, returns an iterator of content chunks.

        Returns:
            Response text (str) or iterator of chunks if stream=True.

        Raises:
            ConnectionError: If the proxy server is unreachable.
            ModelNotFoundError: If the requested model is not available.
        """
        payload: dict = {"messages": messages, "stream": stream}
        if model:
            payload["model"] = model

        if stream:
            return self._stream_response(payload)

        result = self._request("/v1/chat/completions", data=payload)
        return result["choices"][0]["message"]["content"]

    def _stream_response(self, payload: dict) -> Iterator[str]:
        """Stream response chunks via Server-Sent Events."""
        url = f"{self.base_url}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for line in resp:
                    line = line.decode().strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
        except urllib.error.URLError as e:
            raise ProxyConnectionError(
                f"Cannot connect to Copilot Proxy at {self.base_url}. "
                "Is the VS Code extension running?"
            ) from e

    def ask(self, prompt: str, model: str | None = None) -> str:
        """Ask a single question and get a string response.

        Args:
            prompt: The question or prompt text.
            model: Model ID to use (e.g. 'gpt-4.1'). None for default.

        Returns:
            The model's response as a string.
        """
        result = self.chat([{"role": "user", "content": prompt}], model=model)
        if isinstance(result, str):
            return result
        return "".join(result)


class AsyncCopilotClient:
    """Async client for the Copilot Proxy server.

    Drop-in async counterpart of :class:`CopilotClient`.  The constructor
    signature is identical so callers can swap one for the other with no
    other code changes.

    All I/O is offloaded to a thread-pool executor via
    :func:`asyncio.to_thread`, preserving zero runtime dependencies.

    Args:
        base_url: URL of the proxy server (default: http://127.0.0.1:19823).
        timeout: Request timeout in seconds (default: 120).
    """

    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _sync_request(self, path: str, data: dict | None = None, method: str = "GET") -> dict:
        """Synchronous HTTP request — identical logic to CopilotClient._request."""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        if body:
            method = "POST"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            if isinstance(e, urllib.error.HTTPError):
                try:
                    err_body = json.loads(e.read())
                    msg = err_body.get("error", str(e))
                except Exception:
                    msg = str(e)
                if e.code == 404:
                    raise ModelNotFoundError(msg) from e
                raise CopilotProxyError(msg) from e
            raise ProxyConnectionError(
                f"Cannot connect to Copilot Proxy at {self.base_url}. "
                "Is the VS Code extension running? Try reloading VS Code."
            ) from e

    async def _request(self, path: str, data: dict | None = None, method: str = "GET") -> dict:
        """Make an async HTTP request by running sync urllib in a thread pool."""
        return await asyncio.to_thread(self._sync_request, path, data, method)

    async def is_running(self) -> bool:
        """Check if the proxy server is running and healthy (non-blocking)."""
        try:
            result = await self._request("/health")
            return result.get("status") == "ok"
        except CopilotProxyError:
            return False

    async def list_models(self) -> list[dict]:
        """List available Copilot models (non-blocking).

        Returns:
            List of model dicts with keys: id, family, vendor, version, maxInputTokens.

        Raises:
            ProxyConnectionError: If the proxy server is unreachable.
        """
        result = await self._request("/v1/models")
        return result.get("models") or result.get("data", [])

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Send an async chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model ID to use (e.g. 'gpt-4.1'). None for default.
            stream: If True, returns an async iterator of content chunks.

        Returns:
            Response text (str) or async iterator of chunks if stream=True.

        Raises:
            ProxyConnectionError: If the proxy server is unreachable.
            ModelNotFoundError: If the requested model is not available.
        """
        payload: dict = {"messages": messages, "stream": stream}
        if model:
            payload["model"] = model

        if stream:
            return self._async_stream_response(payload)

        result = await self._request("/v1/chat/completions", data=payload)
        return result["choices"][0]["message"]["content"]

    async def _async_stream_response(self, payload: dict) -> AsyncIterator[str]:
        """Async generator that streams SSE chunks without blocking the event loop.

        The synchronous SSE reader runs in a thread and pushes chunks into an
        asyncio.Queue. A sentinel value of None signals end-of-stream.
        """
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _read_sse() -> None:
            url = f"{self.base_url}/v1/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    for line in resp:
                        line = line.decode().strip()
                        if line.startswith("data: ") and line != "data: [DONE]":
                            data = json.loads(line[6:])
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    loop.call_soon_threadsafe(queue.put_nowait, delta["content"])
            except urllib.error.URLError as e:
                exc = ProxyConnectionError(
                    f"Cannot connect to Copilot Proxy at {self.base_url}. "
                    "Is the VS Code extension running?"
                )
                exc.__cause__ = e
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=_read_sse, daemon=True)
        thread.start()

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            # Drain remaining items so the producer thread can finish cleanly.
            thread.join(timeout=self.timeout)

    async def ask(self, prompt: str, model: str | None = None) -> str:
        """Ask a single question and get a string response.

        Args:
            prompt: The question or prompt text.
            model: Model ID to use (e.g. 'gpt-4.1'). None for default.

        Returns:
            The model's response as a string.
        """
        result = await self.chat([{"role": "user", "content": prompt}], model=model)
        if isinstance(result, str):
            return result
        return "".join([chunk async for chunk in result])


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


def is_running() -> bool:
    """Check if the Copilot Proxy server is running."""
    return _get_client().is_running()


_default_async_client: AsyncCopilotClient | None = None


def _get_async_client() -> AsyncCopilotClient:
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncCopilotClient()
    return _default_async_client


async def async_is_running() -> bool:
    """Check if the Copilot Proxy server is running (async)."""
    return await _get_async_client().is_running()


async def async_list_models() -> list[dict]:
    """List available Copilot models (async)."""
    return await _get_async_client().list_models()


async def async_chat(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """Send async chat completion request to Copilot via proxy."""
    return await _get_async_client().chat(messages, model=model, stream=stream)


async def async_ask(prompt: str, model: str | None = None) -> str:
    """Async helper to ask a single question."""
    return await _get_async_client().ask(prompt, model=model)
