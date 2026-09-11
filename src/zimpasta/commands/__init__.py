"""Command entry points, one module per feature.

A command is a plain function ``(console, session) -> None``. It reads and updates the
``Session``, talks to the user only through the ``Console``, and returns when the user
is done. It must not let invalid input raise; use the helpers in ``zimpasta.prompts``.
Nothing in a command should know how it was invoked, so the menu in ``zimpasta.cli``
stays replaceable.
"""

from collections.abc import Callable

from zimpasta.console import Console
from zimpasta.session import Session

Command = Callable[[Console, Session], None]


def not_implemented(name: str) -> Command:
    """Placeholder command for a feature that has not landed yet."""

    def command(console: Console, session: Session) -> None:
        console.say(f"{name} is not implemented yet.")

    return command
