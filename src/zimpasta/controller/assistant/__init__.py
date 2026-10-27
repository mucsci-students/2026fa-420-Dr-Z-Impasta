"""The AI assistant: a chat that turns requests into the application's own actions.

``session.py`` keeps the transcript and runs each request, ``tools.py`` defines the
actions the model may call, ``prompt.py`` holds the base prompt, and ``client.py`` talks
to OpenAI. See docs/assistant.md.
"""

from zimpasta.controller.assistant.client import (
    AIClient,
    AIError,
    AINotConfigured,
    AIReply,
    ToolCall,
    client_from_environment,
)
from zimpasta.controller.assistant.session import Assistant, ChatBusy, ChatError, PendingNotFound

__all__ = [
    "AIClient",
    "AIError",
    "AINotConfigured",
    "AIReply",
    "Assistant",
    "ChatBusy",
    "ChatError",
    "PendingNotFound",
    "ToolCall",
    "client_from_environment",
]
