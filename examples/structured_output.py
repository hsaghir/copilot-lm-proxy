#!/usr/bin/env python3
"""
Minimal script to call Claude Opus 4.5 via Copilot Proxy.
Demonstrates both regular text and structured output with Pydantic.

Usage: python examples/structured_output.py
"""

import json
import urllib.request

from pydantic import BaseModel

PROXY_URL = "http://127.0.0.1:19823"


def call_llm(prompt: str, model: str = "claude-opus-4.5") -> str:
    """Call LLM via Copilot Proxy."""
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        f"{PROXY_URL}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def parse_json_response(response: str) -> str:
    """Extract JSON from response, handling markdown code blocks."""
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                json_lines.append(line)
        return "\n".join(json_lines)
    return response


class NeuralNetExplanation(BaseModel):
    """Pydantic model for structured output."""

    title: str
    summary: str
    key_concepts: list[str]
    difficulty_level: str


def get_structured[T: BaseModel](
    prompt: str, schema: type[T], model: str = "claude-opus-4.5"
) -> T:
    """Get structured response matching a Pydantic schema."""
    schema_json = schema.model_json_schema()
    full_prompt = f"""{prompt}

Respond with ONLY a valid JSON object matching this schema:
{json.dumps(schema_json, indent=2)}

Output ONLY the JSON, no markdown, no explanation."""

    response = call_llm(full_prompt, model=model)
    json_str = parse_json_response(response)
    return schema.model_validate_json(json_str)


if __name__ == "__main__":
    # Test 1: Regular text
    print("=" * 60)
    print("Test 1: Regular text call to Claude Opus 4.5")
    print("=" * 60)
    response = call_llm("Hey, explain neural nets in 2-3 sentences.")
    print(response)

    # Test 2: Structured output with Pydantic
    print("\n" + "=" * 60)
    print("Test 2: Structured output with Pydantic schema")
    print("=" * 60)
    result = get_structured(
        "Explain neural networks for a beginner.", NeuralNetExplanation
    )
    print(f"Title: {result.title}")
    print(f"Summary: {result.summary}")
    print(f"Key concepts: {result.key_concepts}")
    print(f"Difficulty: {result.difficulty_level}")
