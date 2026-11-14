"""The ``load`` command: read and validate a configuration file into the session.

Usage: ``load <path>``. A bare ``load`` asks for the path and keeps asking until a file
loads. The session is assigned only after validation, so a failed load never replaces a
valid configuration.

Author: Foster VanFleet. Converted to the command model.
"""

from pathlib import Path

from zimpasta.command import CommandError, CommandSpec, Invocation, Positional
from zimpasta.commands.common import PATH_PROMPT, read_into_session
from zimpasta.console import Console
from zimpasta.session import Session

FILE_NOT_FOUND = "File not found."
UNREADABLE = "Unable to read file."
INVALID = "Invalid configuration file."
LOADED = "Configuration loaded successfully."


def load_into_session(session: Session, path: Path) -> str | None:
    """Load ``path`` into the session. Returns a message when it cannot be loaded, else None."""
    match read_into_session(session, path):
        case None:
            return None
        case FileNotFoundError():
            return FILE_NOT_FOUND
        case OSError():
            return UNREADABLE
        case _:
            return INVALID


def load(console: Console, session: Session, invocation: Invocation) -> None:
    """Handler: load the given file, or report why it could not be loaded.

    Raises:
        CommandError: the file is missing, unreadable, or not a valid configuration.
    """
    path = Path(str(invocation.get("path"))).expanduser()
    problem = load_into_session(session, path)
    if problem is not None:
        raise CommandError(problem)
    console.say(LOADED)


def build_load(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    """Builder: ask for a path until one loads, then hand the completed command on."""
    while True:
        raw = console.ask(PATH_PROMPT).strip()
        problem = load_into_session(session, Path(raw).expanduser())
        if problem is None:
            return invocation.with_values({"path": raw})
        console.say(problem)


SPECS = (
    CommandSpec(
        "load",
        positionals=(Positional("path", help="configuration JSON file"),),
        description="Load a configuration file",
        handler=load,
        builder=build_load,
    ),
)
