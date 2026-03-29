"""
Copilot Proxy - Access GitHub Copilot LLMs from Python scripts.

Usage:
    from copilot_proxy import ask, chat, list_models

    response = ask("Explain neural networks")
    response = ask("Hello", model="gpt-4.1")
"""

from .client import (
    AsyncCopilotClient,
    CopilotClient,
    CopilotProxyError,
    ModelNotFoundError,
    ProxyConnectionError,
    ask,
    async_ask,
    async_chat,
    async_is_running,
    async_list_models,
    chat,
    is_running,
    list_models,
)

__all__ = [
    "AsyncCopilotClient",
    "CopilotClient",
    "CopilotProxyError",
    "ProxyConnectionError",
    "ModelNotFoundError",
    "ask",
    "async_ask",
    "async_chat",
    "async_is_running",
    "async_list_models",
    "chat",
    "is_running",
    "list_models",
]
__version__ = "0.3.0"
