"""The chat: one transcript per running app, and the loop that answers each message.

:class:`Assistant` keeps the transcript in the Python process, like the configuration
itself, so it is the same on every page and survives reloading the browser tab. For each
message it sends the base prompt, the current state, the last few turns, and the message
to the model; runs the tools the model calls through the registry; feeds the results
back; and stops when the model answers in text or after :data:`MAX_ROUNDS` rounds.

Every tool outcome is recorded in the transcript as its own entry, from the tool's actual
result rather than the model's wording, so the user sees what really happened even if the
model's reply is wrong or the API fails partway through.

Actions that wait for the user (confirming a deletion, finishing a save) are recorded as
pending entries. :meth:`Assistant.answer` settles them without calling the model again.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from zimpasta.controller.assistant import prompt
from zimpasta.controller.assistant.client import AIClient, AIError, AINotConfigured
from zimpasta.controller.assistant.tools import TOOLS, PendingAction, ToolRegistry, ToolResult

if TYPE_CHECKING:
    from zimpasta.controller.app_controller import AppController

MAX_ROUNDS = 6
"""Model calls one message may take: each round runs the tools the model asked for."""

HISTORY_TURNS = 6
"""Earlier user and assistant messages sent with each request, for follow-ups."""

MAX_ENTRIES = 300
"""Transcript entries kept; older ones are dropped."""

MAX_MESSAGE_LENGTH = 4000

Role = Literal["user", "assistant", "tool", "notice"]


class ChatError(Exception):
    """A chat request that can't be carried out. ``message`` is for the user."""

    code = "chat_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ChatBusy(ChatError):
    code = "chat_busy"

    def __init__(self) -> None:
        super().__init__("The assistant is still working on the last message. Wait for it.")


class PendingNotFound(ChatError):
    code = "not_found"

    def __init__(self, pending_id: str) -> None:
        super().__init__(f"There is no pending action {pending_id!r}.")


@dataclass
class _Pending:
    id: str
    entry_id: str
    tool: str
    action: PendingAction
    state: Literal["waiting", "confirmed", "cancelled", "saved", "expired"] = "waiting"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.action.kind,
            "prompt": self.action.prompt,
            "details": list(self.action.details),
            "revision": self.action.revision,
            "state": self.state,
        }


@dataclass
class _Entry:
    id: str
    role: Role
    text: str
    at: datetime
    tool: str | None = None
    result: dict | None = None
    error: dict | None = None
    pending: _Pending | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "text": self.text,
            "at": self.at.isoformat(timespec="seconds"),
            "tool": self.tool,
            "result": self.result,
            "error": self.error,
            "pending": self.pending.to_dict() if self.pending else None,
        }


class Assistant:
    """The AI chat for one running app."""

    def __init__(
        self,
        app: "AppController",
        *,
        client_factory: Callable[[], AIClient] | None,
        registry: ToolRegistry = TOOLS,
        clock: Callable[[], datetime] = datetime.now,
        unavailable_reason: str | None = None,
    ) -> None:
        """``client_factory`` makes the AI client; ``None`` means this version of the app
        has no assistant, and ``unavailable_reason`` says why."""
        self._app = app
        self._factory = client_factory
        self._client: AIClient | None = None
        self._registry = registry
        self._clock = clock
        self._unavailable = unavailable_reason
        self._lock = threading.Lock()
        self._busy = False
        self._entries: list[_Entry] = []
        self._pending: dict[str, _Pending] = {}
        self._counter = 0

    # ---------------------------------------------------------------- reading

    def availability(self) -> dict:
        """Whether messages can be sent, and if not, why (for the chat panel)."""
        try:
            client = self._connect()
        except AINotConfigured as error:
            return {"available": False, "reason": error.message, "model": None}
        return {"available": True, "reason": None, "model": client.model}

    def summary(self) -> dict:
        """What the app state poll includes, so every page knows when the chat changes."""
        with self._lock:
            last = self._entries[-1].id if self._entries else None
            waiting = sum(p.state == "waiting" for p in self._pending.values())
            return {
                "busy": self._busy,
                "entries": len(self._entries),
                "last_entry": last,
                "waiting": waiting,
                **self.availability(),
            }

    def transcript(self) -> dict:
        with self._lock:
            entries = [entry.to_dict() for entry in self._entries]
            busy = self._busy
        return {"entries": entries, "busy": busy, **self.availability()}

    # ---------------------------------------------------------------- actions

    def send(self, message: str) -> dict:
        """Answer one message. Returns the entries it added and the chat's state.

        Raises:
            AINotConfigured: no API key, or no assistant in this version of the app.
            ChatBusy: another message is still being answered.
            ChatError: the message is empty or too long.
        """
        text = message.strip()
        if not text:
            raise ChatError("Type a request first.", "empty_message")
        if len(text) > MAX_MESSAGE_LENGTH:
            raise ChatError(
                f"That message is too long ({len(text)} characters; the limit is "
                f"{MAX_MESSAGE_LENGTH}).",
                "message_too_long",
            )
        client = self._connect()
        self._begin()
        try:
            history = self._history()
            added = [self._add("user", text)]
            added += self._converse(client, history + [{"role": "user", "content": text}])
        finally:
            self._end()
        return self._reply(added)

    def answer(self, pending_id: str, answer: str, filename: str | None = None) -> dict:
        """Settle a pending action: ``confirm`` or ``cancel`` a confirmation, or report a
        save as ``saved`` or ``cancel``.

        Raises:
            PendingNotFound: no such pending action.
            ChatError: it was already settled, or the answer doesn't fit it.
            ChatBusy: a message is being answered.
        """
        self._begin()
        try:
            with self._lock:
                pending = self._pending.get(pending_id)
            if pending is None:
                raise PendingNotFound(pending_id)
            if pending.state != "waiting":
                raise ChatError(f"That was already {pending.state}.", "pending_settled")
            action = pending.action
            allowed = ("confirm", "cancel") if action.kind == "confirm" else ("saved", "cancel")
            if answer not in allowed:
                raise ChatError(
                    f"Answer {' or '.join(allowed)} for this action, not {answer!r}.",
                    "invalid_answer",
                )
            added = [self._settle(pending, answer, filename)]
        finally:
            self._end()
        return self._reply(added)

    def clear(self) -> dict:
        """Start a fresh transcript. Pending actions are dropped."""
        self._begin()
        try:
            with self._lock:
                self._entries.clear()
                self._pending.clear()
        finally:
            self._end()
        return self._reply([])

    # ------------------------------------------------------------------ inside

    def _connect(self) -> AIClient:
        if self._factory is None:
            raise AINotConfigured(
                self._unavailable or "The AI assistant isn't available in this version."
            )
        if self._client is None:
            self._client = self._factory()
        return self._client

    def _begin(self) -> None:
        with self._lock:
            if self._busy:
                raise ChatBusy()
            self._busy = True

    def _end(self) -> None:
        with self._lock:
            self._busy = False

    def _converse(self, client: AIClient, conversation: list[dict[str, Any]]) -> list[_Entry]:
        added: list[_Entry] = []
        tools = self._registry.definitions()
        request: list[dict[str, Any]] = conversation
        previous: str | None = None
        for _ in range(MAX_ROUNDS):
            try:
                reply = client.respond(
                    instructions=prompt.instructions(self._app),
                    input=request,
                    tools=tools,
                    previous_id=previous,
                )
            except AIError as error:
                added.append(self._failure_notice(error, added))
                return added
            if reply.text:
                added.append(self._add("assistant", reply.text))
            if not reply.calls:
                if not reply.text:
                    added.append(self._add("assistant", "(The assistant didn't reply.)"))
                return added
            outputs = []
            for call in reply.calls:
                result = self._registry.dispatch(self._app, call.name, call.arguments)
                added.append(self._record(call.name, result))
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result.for_model(),
                    }
                )
            request, previous = outputs, reply.id
        added.append(
            self._add(
                "notice",
                f"The assistant stopped after {MAX_ROUNDS} steps without finishing. The "
                "actions listed above are what actually happened. Try a smaller request.",
                error={"code": "too_many_steps", "message": "Stopped after too many steps."},
            )
        )
        return added

    def _failure_notice(self, error: AIError, added: list[_Entry]) -> _Entry:
        ran = [entry for entry in added if entry.role == "tool"]
        text = error.message
        if ran:
            text += " The actions listed above did run; nothing else was changed."
        else:
            text += " Nothing was changed."
        return self._add("notice", text, error={"code": error.code, "message": error.message})

    def _record(self, name: str, result: ToolResult) -> _Entry:
        entry = self._add("tool", result.summary, tool=name, result=result.to_dict())
        if result.pending is not None:
            with self._lock:
                pending = _Pending(self._next("p"), entry.id, name, result.pending)
                self._pending[pending.id] = pending
                entry.pending = pending
        return entry

    def _settle(self, pending: _Pending, answer: str, filename: str | None) -> _Entry:
        action = pending.action
        workspace = self._app.workspace
        if answer == "cancel":
            pending.state = "cancelled"
            text = "Not saved." if action.kind == "save" else "Cancelled. Nothing was changed."
            return self._add("notice", text)
        if action.kind == "save":
            if workspace.saved_revision < action.revision:
                raise ChatError(
                    "The configuration isn't marked saved yet. Finish saving the file first.",
                    "not_saved",
                )
            pending.state = "saved"
            name = filename or workspace.name or "the file"
            return self._add(
                "tool",
                f"Saved the configuration as {name}.",
                tool="save_configuration",
                result={"status": "done", "ok": True, "summary": f"Saved as {name}."},
            )
        if workspace.revision != action.revision:
            pending.state = "expired"
            return self._add(
                "notice",
                "The configuration changed after this was proposed, so nothing was done. "
                "Ask again to see the current effect.",
                error={"code": "pending_expired", "message": "The configuration changed."},
            )
        pending.state = "confirmed"
        run = action.run
        if run is None:
            raise ChatError("This action has nothing to run.", "invalid_answer")
        return self._record(pending.tool, run())

    def _history(self) -> list[dict[str, Any]]:
        with self._lock:
            turns = [entry for entry in self._entries if entry.role in ("user", "assistant")]
        return [{"role": entry.role, "content": entry.text} for entry in turns[-HISTORY_TURNS:]]

    def _add(self, role: Role, text: str, **details: Any) -> _Entry:
        with self._lock:
            entry = _Entry(self._next("m"), role, text, self._clock(), **details)
            self._entries.append(entry)
            if len(self._entries) > MAX_ENTRIES:
                del self._entries[: len(self._entries) - MAX_ENTRIES]
            return entry

    def _next(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def _reply(self, added: list[_Entry]) -> dict:
        return {
            "added": [entry.to_dict() for entry in added],
            "state": self._app.state(),
        }
