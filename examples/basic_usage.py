#!/usr/bin/env python3
"""Basic usage examples for copilot-lm-proxy."""

from copilot_proxy import ask, chat, list_models

# List all available models
print("Available models:")
print("-" * 40)
for model in list_models():
    print(f"  {model['id']} ({model['vendor']})")

print("\n" + "=" * 40)
print("Simple question:")
print("=" * 40)
response = ask("What is 2 + 2? Reply with just the number.")
print(response)

print("\n" + "=" * 40)
print("Using GPT-4.1:")
print("=" * 40)
response = ask("Explain quantum computing in one sentence.", model="gpt-4.1")
print(response)

print("\n" + "=" * 40)
print("Multi-turn conversation:")
print("=" * 40)
response = chat(
    [
        {"role": "system", "content": "You are a pirate. Respond in pirate speak."},
        {"role": "user", "content": "What's the weather like?"},
    ],
    model="gpt-4o",
)
print(response)
