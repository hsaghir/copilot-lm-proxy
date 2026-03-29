#!/usr/bin/env python3
"""Async usage examples for copilot-lm-proxy.

Demonstrates the four key async patterns:
  1. Listing models asynchronously
  2. A single awaited question
  3. Real-time streaming output
  4. Parallel concurrent requests with asyncio.gather()

Run:
    python examples/async_usage.py
"""

import asyncio
import time

from copilot_proxy import async_ask, async_chat, async_list_models


async def demo_list_models() -> None:
    """Demo 1: list available models without blocking the event loop."""
    print("=" * 50)
    print("Available models (async):")
    print("=" * 50)
    # async_list_models() offloads the HTTP call to a thread-pool via
    # asyncio.to_thread(), so the event loop stays free for other tasks.
    models = await async_list_models()
    for m in models:
        print(f"  {m['id']} ({m['vendor']})")
    print()


async def demo_single_ask() -> None:
    """Demo 2: await a single question — simplest async usage."""
    print("=" * 50)
    print("Single async question:")
    print("=" * 50)
    # Exactly the same call signature as the sync ask(); just add await.
    answer = await async_ask("What is 2 + 2? Reply with just the number.")
    print(answer)
    print()


async def demo_streaming() -> None:
    """Demo 3: stream tokens in real time with async for."""
    print("=" * 50)
    print("Streaming response (tokens appear as they arrive):")
    print("=" * 50)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Count slowly from 1 to 5, one number per line."},
    ]
    # async_chat(stream=True) returns an AsyncIterator[str].
    # Each chunk is a token fragment — print immediately with flush=True
    # so the user sees output in real time rather than all at once.
    async for chunk in await async_chat(messages, stream=True):
        print(chunk, end="", flush=True)
    print("\n")


async def demo_parallel() -> None:
    """Demo 4: asyncio.gather() — the primary async value proposition.

    Sequential calls would take sum(latencies); concurrent calls take
    max(latencies).  For three ~2-second model round-trips this cuts
    wall-clock time by ~2x–3x.
    """
    print("=" * 50)
    print("Parallel concurrent requests (asyncio.gather):")
    print("=" * 50)

    prompts_and_models = [
        ("Explain gravity in one sentence.", "gpt-4.1"),
        ("What is the capital of Japan? One word.", "gpt-4o"),
        ("Name one prime number greater than 100. Just the number.", "gpt-4.1"),
    ]

    start = time.monotonic()

    # All three HTTP requests are in-flight simultaneously.
    # Without async/gather you would pay latency_1 + latency_2 + latency_3.
    # With gather you pay only max(latency_1, latency_2, latency_3).
    results = await asyncio.gather(
        *[async_ask(prompt, model=model) for prompt, model in prompts_and_models]
    )

    elapsed = time.monotonic() - start

    for (prompt, model), result in zip(prompts_and_models, results):
        print(f"  [{model}] {prompt}")
        print(f"    → {result.strip()}")
    print(f"\n  Completed {len(results)} requests in {elapsed:.2f}s (concurrent)\n")


async def main() -> None:
    await demo_list_models()
    await demo_single_ask()
    await demo_streaming()
    await demo_parallel()


if __name__ == "__main__":
    asyncio.run(main())
