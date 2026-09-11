"""Console abstraction so commands can be scripted in tests and hosted by any shell."""

from typing import Protocol


class Console(Protocol):
    """Minimal text I/O surface used by every command."""

    def ask(self, prompt: str) -> str:
        """Show ``prompt`` and return one line of user input without the trailing newline."""
        ...

    def say(self, text: str = "") -> None:
        """Print one line of output."""
        ...


class StdConsole:
    """Console backed by the built-in ``input`` and ``print``."""

    def ask(self, prompt: str) -> str:
        return input(prompt)

    def say(self, text: str = "") -> None:
        print(text)
