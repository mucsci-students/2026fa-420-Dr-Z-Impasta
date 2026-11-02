"""The connection to OpenAI, behind a small interface the rest of the assistant uses.

:class:`AIClient` is all the assistant needs: send instructions, input, and tool
definitions, and get back text and tool calls. :class:`OpenAIClient` adapts the OpenAI
Python SDK's Responses API to it (the Adapter pattern), so tests use a scripted fake and
nothing else in the application imports ``openai``. The SDK is imported only when a client
is created, which keeps the browser version, which has neither a key nor the ``openai``
package, working.

Configuration comes from the environment:

``OPENAI_API_KEY``
    The API key. Without it the assistant reports that it isn't configured.
``ZIMPASTA_AI_MODEL``
    The model, ``gpt-6-luna`` unless set.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_MODEL = "gpt-6-luna"
KEY_VARIABLE = "OPENAI_API_KEY"
MODEL_VARIABLE = "ZIMPASTA_AI_MODEL"

REQUEST_TIMEOUT = 60.0
"""Seconds to wait for one API call."""

MAX_RETRIES = 1
"""Retries the SDK makes for a failed call (connection errors, 429, 5xx). Kept low so a
failing API never turns one chat message into many paid requests."""

MAX_OUTPUT_TOKENS = 2000
"""Upper bound on what one call can generate: a reply or a batch of tool calls."""


@dataclass(frozen=True)
class ToolCall:
    """One function call the model asked for."""

    call_id: str
    name: str
    arguments: str
    """The arguments as the model sent them: JSON text, not yet checked."""


@dataclass(frozen=True)
class AIReply:
    """What one call returned: text, tool calls, or both."""

    id: str | None
    text: str = ""
    calls: tuple[ToolCall, ...] = ()


class AIError(Exception):
    """The AI service couldn't answer. ``message`` says why, for the user."""

    code = "ai_unavailable"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AINotConfigured(AIError):
    """No API key, or the assistant isn't available in this version of the app."""

    code = "ai_not_configured"


class AIClient(Protocol):
    """Sends one request to a language model."""

    model: str

    def respond(
        self,
        *,
        instructions: str,
        input: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_id: str | None = None,
    ) -> AIReply:
        """Ask the model. ``previous_id`` continues an earlier reply in the same request,
        in which case ``input`` holds only the tool results.

        Raises:
            AIError: the request failed; the message says why.
        """
        ...


class OpenAIClient:
    """:class:`AIClient` on the OpenAI Responses API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, *, sdk: Any = None) -> None:
        """``sdk`` replaces ``openai.OpenAI`` in tests; normally it is created here."""
        if sdk is None:
            import openai

            sdk = openai.OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES)
        self._sdk = sdk
        self.model = model

    def respond(
        self,
        *,
        instructions: str,
        input: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_id: str | None = None,
    ) -> AIReply:
        options: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input,
            "tools": tools,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        if previous_id is not None:
            options["previous_response_id"] = previous_id
        try:
            response = self._sdk.responses.create(**options)
        except Exception as error:
            raise AIError(self._explain(error)) from error
        calls = tuple(
            ToolCall(call_id=item.call_id, name=item.name, arguments=item.arguments)
            for item in response.output
            if getattr(item, "type", None) == "function_call"
        )
        text = (response.output_text or "").strip()
        if not calls and not text:
            reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
            raise AIError(
                "The AI stopped without answering"
                + (f" ({str(reason).replace('_', ' ')})." if reason else ".")
            )
        return AIReply(id=response.id, text=text, calls=calls)

    def _explain(self, error: Exception) -> str:
        """A sentence for the user. The key itself never appears in it."""
        import openai

        match error:
            case openai.AuthenticationError() | openai.PermissionDeniedError():
                return f"OpenAI rejected the API key. Check {KEY_VARIABLE} and restart the app."
            case openai.RateLimitError():
                return (
                    "OpenAI is limiting requests right now (rate limit or quota). "
                    "Wait a minute and try again."
                )
            case openai.NotFoundError():
                return (
                    f"OpenAI doesn't offer the model {self.model!r} to this key. "
                    f"Check {MODEL_VARIABLE}."
                )
            case openai.APITimeoutError():
                return "OpenAI didn't answer in time. Try again."
            case openai.APIConnectionError():
                return "Couldn't reach OpenAI. Check your internet connection and try again."
            case openai.BadRequestError():
                return f"OpenAI couldn't process the request: {_short(error)}"
            case openai.APIStatusError():
                return f"OpenAI had a problem (HTTP {error.status_code}). Try again."
            case _:
                return f"The request to OpenAI failed: {_short(error)}"


def client_from_environment(environ: Mapping[str, str] | None = None) -> OpenAIClient:
    """The OpenAI client configured by the environment.

    Raises:
        AINotConfigured: ``OPENAI_API_KEY`` isn't set.
    """
    environ = os.environ if environ is None else environ
    key = environ.get(KEY_VARIABLE, "").strip()
    if not key:
        raise AINotConfigured(
            f"The AI assistant needs an OpenAI API key. Set {KEY_VARIABLE} in the environment "
            "and restart the app (see docs/assistant.md)."
        )
    model = environ.get(MODEL_VARIABLE, "").strip() or DEFAULT_MODEL
    return OpenAIClient(key, model)


def _short(error: Exception, limit: int = 200) -> str:
    text = getattr(error, "message", None) or str(error) or type(error).__name__
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
