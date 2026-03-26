"""
Copilot Proxy - Access GitHub Copilot LLMs from Python scripts.

Usage:
    from copilot_proxy import ask, chat, list_models

    response = ask("Explain neural networks")
    response = ask("Hello", model="gpt-4.1")
"""

from .client import (
    CopilotClient,
    CopilotProxyError,
    ModelNotFoundError,
    ProxyConnectionError,
    ask,
    chat,
    is_running,
    list_models,
)

__all__ = [
    "CopilotClient",
    "CopilotProxyError",
    "ProxyConnectionError",
    "ModelNotFoundError",
    "ask",
    "chat",
    "is_running",
    "list_models",
]
__version__ = "0.2.0"
