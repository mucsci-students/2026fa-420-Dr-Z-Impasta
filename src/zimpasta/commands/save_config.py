"""The ``save`` command: write the session's configuration to a JSON file.

Usage: ``save <path>``. A bare ``save`` asks for the path, offering the loaded file's
path as the default. The file is written with the library's serializer, so it loads
back unchanged.

Author: Foster VanFleet. Converted to the command model.
"""

from pathlib import Path

from zimpasta.command import CommandSpec, Invocation, Positional
from zimpasta.console import Console
from zimpasta.session import Session

NO_CONFIG = "No configuration is loaded."
PATH_PROMPT = "Enter configuration file path: "
PATH_PROMPT_WITH_DEFAULT = "Enter configuration file path [{default}]: "
BLANK_PATH = "Enter a file name."
UNWRITABLE = "Unable to save configuration."
SAVED = "Configuration saved successfully."


def save(console: Console, session: Session, invocation: Invocation) -> None:
    """Handler: write the configuration to the given path and remember that path."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    path = Path(str(invocation.get("path"))).expanduser()
    try:
        path.write_text(session.config.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        console.say(UNWRITABLE)
        return
    session.config_path = path.resolve()
    console.say(SAVED)


def build_save(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    """Builder: ask where to save; Enter keeps the loaded file's path when there is one."""
    if session.config is None:
        console.say(NO_CONFIG)
        return None
    default = session.config_path
    while True:
        prompt = PATH_PROMPT_WITH_DEFAULT.format(default=default) if default else PATH_PROMPT
        raw = console.ask(prompt).strip()
        if raw:
            return invocation.with_values({"path": raw})
        if default is not None:
            return invocation.with_values({"path": str(default)})
        console.say(BLANK_PATH)


SPECS = (
    CommandSpec(
        "save",
        positionals=(Positional("path", help="where to write the configuration JSON"),),
        description="Save the loaded configuration to a file",
        handler=save,
        builder=build_save,
    ),
)
