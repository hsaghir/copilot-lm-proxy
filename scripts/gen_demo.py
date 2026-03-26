#!/usr/bin/env python3
"""Generate an asciicast v2 recording for the demo."""

import json
import time

WIDTH = 80
HEIGHT = 24

# Asciicast v2 header
header = {
    "version": 2,
    "width": WIDTH,
    "height": HEIGHT,
    "timestamp": int(time.time()),
    "title": "Copilot Proxy Demo",
    "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
}


def type_text(text: str, start: float, char_delay: float = 0.05) -> list:
    """Simulate typing character by character."""
    events = []
    t = start
    for ch in text:
        events.append([round(t, 3), "o", ch])
        t += char_delay
    return events


def output(text: str, t: float) -> list:
    """Instant output."""
    return [[round(t, 3), "o", text]]


events = []
t = 0.5

# Prompt
events += output("$ ", t)
t += 0.3

# Type pip install
events += type_text("pip install copilot-proxy", t, 0.04)
t += len("pip install copilot-proxy") * 0.04 + 0.2
events += output("\r\n", t)
t += 0.3
events += output("Successfully installed copilot-proxy-0.1.0\r\n", t)
t += 0.8

# Prompt
events += output("$ ", t)
t += 0.5

# Type python command
cmd = 'python -c "from copilot_proxy import ask; print(ask(\'Hello!\'))"'
events += type_text(cmd, t, 0.03)
t += len(cmd) * 0.03 + 0.3
events += output("\r\n", t)
t += 1.5

# LLM response
response = "Hello! How can I help you today?"
events += output(response + "\r\n", t)
t += 0.8

# Prompt
events += output("$ ", t)
t += 0.5

# Type python for multi-model
cmd2 = 'python -c "from copilot_proxy import ask; print(ask(\'2+2?\', model=\'gpt-4.1\'))"'
events += type_text(cmd2, t, 0.03)
t += len(cmd2) * 0.03 + 0.3
events += output("\r\n", t)
t += 1.2
events += output("4\r\n", t)
t += 0.8

# Prompt
events += output("$ ", t)
t += 0.5

# List models
cmd3 = 'python -c "from copilot_proxy import list_models; [print(m[\'id\']) for m in list_models()[:5]]"'
events += type_text(cmd3, t, 0.025)
t += len(cmd3) * 0.025 + 0.3
events += output("\r\n", t)
t += 0.8
models = "gpt-4.1\r\ngpt-4o\r\nclaude-sonnet-4.6\r\nclaude-opus-4.6\r\ngemini-2.5-pro\r\n"
events += output(models, t)
t += 1.0

events += output("$ ", t)
t += 1.5

# Write the cast file
lines = [json.dumps(header)]
for event in events:
    lines.append(json.dumps(event))

with open("assets/demo.cast", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Written {len(events)} events, {t:.1f}s total")
