#!/usr/bin/env python3
"""Generate a demo SVG image showing copilot-proxy usage."""

from html import escape

CHAR_W = 8.4
CHAR_H = 18
PADDING = 20
TITLE_H = 30
COLS = 85

lines = [
    ("prompt", "$ pip install copilot-lm-proxy"),
    ("output", "Successfully installed copilot-lm-proxy-0.1.0"),
    ("blank", ""),
    ("prompt", '$ python -c "from copilot_proxy import ask; print(ask(\'Hello!\'))"'),
    ("output", "Hello! How can I help you today?"),
    ("blank", ""),
    ("prompt", '$ python -c "from copilot_proxy import ask; print(ask(\'2+2?\', model=\'gpt-4.1\'))"'),
    ("output", "4"),
    ("blank", ""),
    ("prompt", '$ python -c "from copilot_proxy import list_models; [print(m[\'id\']) for m in list_models()[:5]]"'),
    ("output", "gpt-4.1"),
    ("output", "gpt-4o"),
    ("output", "claude-sonnet-4.6"),
    ("output", "claude-opus-4.6"),
    ("output", "gemini-2.5-pro"),
]

svg_w = int(COLS * CHAR_W + PADDING * 2)
svg_h = int(len(lines) * CHAR_H + PADDING * 2 + TITLE_H + 10)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}">
  <rect width="100%" height="100%" rx="8" fill="#1e1e2e"/>
  <circle cx="20" cy="15" r="6" fill="#ff5f57"/>
  <circle cx="38" cy="15" r="6" fill="#febc2e"/>
  <circle cx="56" cy="15" r="6" fill="#28c840"/>
  <text x="{svg_w // 2}" y="17" fill="#6c7086" font-size="12" font-family="monospace" text-anchor="middle">copilot-proxy demo</text>
  <g transform="translate({PADDING},{PADDING + TITLE_H})">
'''

y = CHAR_H
for kind, text in lines:
    escaped = escape(text)
    if kind == "prompt":
        # $ in green, rest in blue
        svg += f'    <text x="0" y="{y}" font-size="14" font-family="Menlo,Monaco,Consolas,monospace" xml:space="preserve"><tspan fill="#a6e3a1">$ </tspan><tspan fill="#89b4fa">{escape(text[2:])}</tspan></text>\n'
    elif kind == "output":
        svg += f'    <text x="0" y="{y}" fill="#cdd6f4" font-size="14" font-family="Menlo,Monaco,Consolas,monospace" xml:space="preserve">{escaped}</text>\n'
    y += CHAR_H

svg += "  </g>\n</svg>\n"

with open("assets/demo.svg", "w") as f:
    f.write(svg)

print(f"Written assets/demo.svg ({svg_w}x{svg_h})")
