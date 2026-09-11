"""Test doubles shared across the suite."""

from collections.abc import Iterable


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
