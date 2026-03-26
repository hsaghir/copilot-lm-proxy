"""
Copilot Proxy - Access GitHub Copilot LLMs from Python scripts.

Usage:
    from copilot_proxy import ask, chat, list_models

    response = ask("Explain neural networks")
    response = ask("Hello", model="gpt-4.1")
"""

from .client import (
    ConnectionError,
    CopilotClient,
    CopilotProxyError,
    ModelNotFoundError,
    ask,
    chat,
    list_models,
)

__all__ = [
    "CopilotClient",
    "CopilotProxyError",
    "ConnectionError",
    "ModelNotFoundError",
    "ask",
    "chat",
    "list_models",
]
__version__ = "0.1.0"
