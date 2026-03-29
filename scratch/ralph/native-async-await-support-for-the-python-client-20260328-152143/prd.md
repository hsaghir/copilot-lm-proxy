# PRD: Native Async/Await Support for the Python Client

## Problem

The `copilot_proxy` Python client is entirely synchronous, which is a fundamental architectural mismatch with the modern Python AI ecosystem. Every major AI agent framework (LangGraph, LangChain, AutoGen, CrewAI), every async web framework (FastAPI, Starlette, aiohttp), and every async notebook environment (JupyterLab) expects async-compatible APIs. Using the current synchronous client inside any of these contexts blocks the event loop, degrades throughput, and makes parallel model calls impossible without resorting to threads.

## Solution

Add an `AsyncCopilotClient` class alongside the existing `CopilotClient`, plus module-level `async_ask`, `async_chat`, and `async_list_models` convenience functions. Python 3.10+ has asyncio built-in, so this can be done with zero new runtime dependencies — preserving the project's core "zero dependencies" philosophy.

Non-blocking HTTP is implemented via `asyncio.to_thread()` wrapping the existing sync urllib calls, which is idiomatic, robust, and avoids reimplementing raw HTTP over asyncio streams. Async streaming uses `asyncio.Queue` to bridge the sync SSE reader thread with an async generator consumer.

## Value Proposition

This single structural change unlocks the proxy for the entire class of async Python applications:

- **FastAPI / Starlette**: `await` model calls in route handlers without blocking other requests
- **Parallel queries**: `asyncio.gather()` to fire off multiple model calls concurrently and collect results
- **Streaming in websockets**: consume streamed responses with `async for` in websocket handlers
- **Agent orchestration**: compose the client naturally inside async agent loops (LangGraph, AutoGen, CrewAI)

It doubles the surface area of the public API in a fully backward-compatible way and positions the library as a first-class citizen in modern Python AI development.

---

## Phase 1: Core Async Implementation

### Task 1.1 — Add AsyncCopilotClient class with async request primitives

Add the `AsyncCopilotClient` class to `src/copilot_proxy/client.py`. Implement `async def _request(path, data, method)` using `asyncio.to_thread()` to run the existing synchronous urllib logic in a thread-pool executor, keeping zero runtime dependencies. Add `async def is_running() -> bool` and `async def list_models() -> list[dict]` that delegate to the async `_request`. The class constructor signature must match `CopilotClient(base_url, timeout)` exactly so users can swap in `AsyncCopilotClient` as a drop-in with no other code changes. Add `from collections.abc import AsyncIterator` under `if TYPE_CHECKING:` as a best-practice annotation guard, or rely on the existing `from __future__ import annotations` — both are acceptable on Python 3.10+.

**Verification**: `python -c "import asyncio; from copilot_proxy import AsyncCopilotClient; print('Import OK')"` (smoke-import check; full async test coverage is delivered in task 2.2).

### Task 1.2 — Implement async def chat() with non-streaming and async streaming support

Add `async def chat(messages, model, stream)` to `AsyncCopilotClient`. For non-streaming mode, delegate to `async _request` and extract `choices[0].message.content`. For streaming mode, implement `_async_stream_response()` as an async generator: spin up the synchronous SSE reader in a thread via `asyncio.to_thread` or `loop.run_in_executor`, push each yielded string chunk into an `asyncio.Queue`, and yield chunks from the queue in the async generator on the caller side. The sentinel value `None` signals end-of-stream. The method signature must return `Union[str, AsyncIterator[str]]` and callers must be able to use `async for chunk in client.chat(..., stream=True)`. Also add `async def ask(prompt, model) -> str` as a thin wrapper over `chat`.

**Verification**: `python -c "import asyncio; from copilot_proxy.client import AsyncCopilotClient; print('AsyncCopilotClient OK')"` (smoke-import check; full test coverage in task 2.2).

### Task 1.3 — Add module-level async convenience functions and export from __init__.py

Add module-level async convenience functions `async_ask(prompt, model)`, `async_chat(messages, model, stream)`, and `async_list_models()` to `src/copilot_proxy/client.py`, mirroring the pattern of the existing synchronous `ask`/`chat`/`list_models` functions. Maintain a module-level `_default_async_client: AsyncCopilotClient | None = None` and a `_get_async_client()` factory that lazily creates the singleton, respecting the `COPILOT_PROXY_URL` environment variable. Export `AsyncCopilotClient`, `async_ask`, `async_chat`, and `async_list_models` from `src/copilot_proxy/__init__.py` and add them to `__all__`. Bump `__version__` to `0.3.0` in both `__init__.py` and `pyproject.toml`.

**Verification**: `pytest tests/test_client.py -v` (the file that currently exists; full two-file run is in task 2.2+).

---

## Phase 2: Testing

### Task 2.1 — Add pytest-asyncio dev dependency and configure asyncio test mode

Add `pytest-asyncio>=0.23` to the `[project.optional-dependencies]` dev list in `pyproject.toml`. Set `asyncio_mode = 'auto'` under `[tool.pytest.ini_options]` so that all async test functions are automatically recognized without needing the `@pytest.mark.asyncio` decorator on each one. Verify the existing synchronous tests in `tests/test_client.py` still pass unmodified.

**Verification**: `pip install -e '.[dev]' && pytest tests/test_client.py -v`

### Task 2.2 — Write comprehensive async unit tests in tests/test_async_client.py

Move the `mock_server` fixture and its supporting code (`MockProxyHandler`, `MOCK_MODELS`) from `tests/test_client.py` into `tests/conftest.py` so it can be shared between both test files. Create `tests/test_async_client.py` that mirrors the structure of `tests/test_client.py`. Write async tests for: `AsyncCopilotClient.list_models()`, `is_running()` returning True and False, `ask()` and `chat()` returning strings, `chat(stream=True)` producing chunks via `async for`, `ModelNotFoundError` on nonexistent-model, `ProxyConnectionError` on bad port, trailing slash in `base_url`, unicode and long prompts, and all three module-level async functions (`async_ask`, `async_chat`, `async_list_models`) using `unittest.mock.patch` on `_default_async_client`. Aim for at least 15 test cases.

**Verification**: `pytest tests/test_async_client.py -v`

---

## Phase 3: Documentation and Examples

### Task 3.1 — Add async usage section to README.md

Add a new `### Async Python Client` section to `README.md` immediately after the existing `### Python Client (zero dependencies)` section. The section must include a standalone code example demonstrating: (1) `await async_ask(prompt, model)` for a single call, (2) `await async_chat(messages, stream=False)` for a multi-turn exchange, (3) `async for chunk in async_chat(messages, stream=True)` for streaming output, and (4) `asyncio.gather(*[async_ask(p) for p in prompts])` to show the primary value proposition of parallel concurrent requests. Add a brief note that `AsyncCopilotClient` is a drop-in replacement for `CopilotClient` for use in async frameworks like FastAPI.

**Verification**: `python -m doctest README.md --option ELLIPSIS || true`

### Task 3.2 — Add examples/async_usage.py with runnable async examples

Create `examples/async_usage.py` as a standalone runnable script demonstrating async capabilities. The script should use `asyncio.run(main())` at the bottom and define an `async main()` that runs four demonstrations: (1) `await async_list_models()` to print available models, (2) `await async_ask()` for a simple question, (3) async streaming with `async for` to print chunks in real-time with `end=''` flush, and (4) `asyncio.gather()` to send three different prompts to three different models concurrently and print all results with wall-clock timing showing the speedup over sequential calls. Include inline comments explaining why each pattern is valuable. The script must be importable (guard the `asyncio.run` call with `if __name__ == '__main__'`).

**Verification**: `python -c 'import ast, sys; ast.parse(open("examples/async_usage.py").read()); print("Syntax OK")'`
