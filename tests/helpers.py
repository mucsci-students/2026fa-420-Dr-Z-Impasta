"""Test doubles shared across the suite."""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from scheduler import CombinedConfig

from zimpasta.controller.assistant import AIReply, ToolCall
from zimpasta.model.generate import Schedule

FIXTURE_CONFIG = Path(__file__).resolve().parent / "fixtures" / "minimal_config.json"
"""Two courses, two faculty: the library solves it in milliseconds, so tests use it."""

EXAMPLE_CONFIG = Path(__file__).resolve().parents[1] / "examples" / "sample_config.json"
"""The realistic department example shipped for users; solved once, in tests/test_examples.py."""


def load_sample_config_data() -> dict:
    """A fresh copy of the small test fixture as plain JSON data."""
    return json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8"))


def build_config_data(*, limit: int = 2, optimizer_flags: list[str] | None = None) -> dict:
    """The test fixture with a chosen limit and optional optimizer flags."""
    data = load_sample_config_data()
    data["limit"] = limit
    if optimizer_flags is not None:
        data["optimizer_flags"] = optimizer_flags
    return data


def build_infeasible_config_data() -> dict:
    """The test fixture with no faculty available on Monday, where every class meets."""
    data = build_config_data()
    for faculty in data["config"]["faculty"]:
        faculty["times"] = {"TUE": ["08:00-18:00"]}
    return data


class ScriptExhausted(AssertionError):
    """A command asked for more input than the test scripted."""


class ScriptedConsole:
    """Console that answers prompts from a fixed script and records everything said.

    Usage::

        console = ScriptedConsole(["2", "yes"])
        my_command(console, session)
        assert "Done." in console.output
    """

    def __init__(self, answers: Iterable[str] = ()) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.output: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise ScriptExhausted(f"no scripted answer for prompt {prompt!r}")
        return self.answers.pop(0)

    def say(self, text: str = "") -> None:
        self.output.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.output)


class FakeScheduler:
    """Stands in for ``scheduler.Scheduler`` and yields canned schedules."""

    def __init__(
        self,
        config: CombinedConfig,
        *,
        solver_timeout_ms: int | None = None,
        schedules: Iterable[Schedule] = (),
        reason: str | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.config = config
        self.solver_timeout_ms = solver_timeout_ms
        self._schedules = list(schedules)
        self._reason = reason
        self._error = error
        self._enumeration_completion_reason: str | None = None

    def get_models(self) -> Iterator[Schedule]:
        self._enumeration_completion_reason = None
        if self._error is not None:
            raise self._error
        for index, schedule in enumerate(self._schedules):
            if index >= self.config.limit:
                return
            yield schedule
        if len(self._schedules) < self.config.limit:
            self._enumeration_completion_reason = self._reason


class FakeSchedulerFactory:
    """Callable with the ``Scheduler`` signature that records every construction."""

    def __init__(
        self,
        schedules: Iterable[Schedule] = (),
        *,
        reason: str | None = "solution_space_exhausted",
        error: BaseException | None = None,
    ) -> None:
        self.schedules = list(schedules)
        self.reason = reason
        self.error = error
        self.instances: list[FakeScheduler] = []

    def __call__(self, config: CombinedConfig, *, solver_timeout_ms: int | None = None):
        instance = FakeScheduler(
            config,
            solver_timeout_ms=solver_timeout_ms,
            schedules=self.schedules,
            reason=self.reason,
            error=self.error,
        )
        self.instances.append(instance)
        return instance

    @property
    def last_config(self) -> CombinedConfig:
        return self.instances[-1].config


class FakeAIClient:
    """Stands in for OpenAI: returns scripted replies and records every request.

    Each script step is an ``AIReply`` to return, an exception to raise, or a callable that
    receives the request and returns a reply. Asking for more than the script holds fails
    the test, so a test also proves how many API calls a message makes::

        ai = FakeAIClient(calling(tool_call("validate_configuration")), saying("It's valid."))
    """

    model = "fake-model"

    def __init__(self, *script) -> None:
        self.script = list(script)
        self.requests: list[dict] = []

    def respond(self, *, instructions, input, tools, previous_id=None) -> AIReply:
        request = {
            "instructions": instructions,
            "input": input,
            "tools": tools,
            "previous_id": previous_id,
        }
        self.requests.append(request)
        if not self.script:
            raise AssertionError("The fake AI was asked more often than the test scripted.")
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        if callable(step):
            return step(request)
        return step


def tool_call(name: str, call_id: str = "call-1", **arguments) -> ToolCall:
    """A tool call as the model would send it, with JSON-encoded arguments."""
    return ToolCall(call_id=call_id, name=name, arguments=json.dumps(arguments))


def calling(*calls: ToolCall, reply_id: str = "reply-1") -> AIReply:
    return AIReply(id=reply_id, calls=calls)


def saying(text: str, reply_id: str = "reply-final") -> AIReply:
    return AIReply(id=reply_id, text=text)
