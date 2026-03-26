"""
Copilot Proxy - Access GitHub Copilot LLMs from Python scripts.

Usage:
    from copilot_proxy import ask, chat, list_models

    response = ask("Explain neural networks")
    response = ask("Hello", model="claude-opus-4.5")
"""

from .client import CopilotClient, ask, chat, list_models

__all__ = ["CopilotClient", "ask", "chat", "list_models"]
__version__ = "0.1.0"
