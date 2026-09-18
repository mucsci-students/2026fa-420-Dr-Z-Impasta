"""Shell entry point: welcome page, command prompt, dispatch.

The shell is a REPL. A complete command line such as
``run schedule --limit 5 --optimize yes --format csv --output out`` runs immediately. A
bare verb, or a command missing required parts, engages that command's builder, which
asks for the missing pieces and then runs the same command through the evaluator.

To wire in your feature, put your ``CommandSpec``s in ``zimpasta/commands/<feature>.py``
as ``SPECS`` and swap them in for your placeholder in ``PLACEHOLDERS`` below, the way
``delete`` does. The remaining placeholders carry the agreed grammar so ``help`` is
accurate before a feature lands.
"""

from collections.abc import Iterable

from zimpasta.command import (
    CommandError,
    CommandSpec,
    Invocation,
    Positional,
    QuitShell,
    Registry,
    UnknownCommand,
    evaluate,
)
from zimpasta.commands.delete import SPECS as DELETE_SPECS
from zimpasta.commands.display_schedules import SPECS as DISPLAY_SPECS
from zimpasta.commands.help import format_help, help_spec

from zimpasta.commands.modify import MODIFY_SPECS

from zimpasta.commands.load_config import SPECS as LOAD_SPECS
from zimpasta.commands.print_config import SPECS as PRINT_SPECS

from zimpasta.commands.results import SPECS as SCHEDULES_SPECS
from zimpasta.commands.run import SPECS as RUN_SPECS
from zimpasta.commands.save_config import SPECS as SAVE_SPECS
from zimpasta.console import Console, StdConsole
from zimpasta.generate import quiet_library_logging
from zimpasta.prompts import INVALID_CHOICE
from zimpasta.session import Session
from zimpasta.welcome_page import welcome

KINDS = ("course", "room", "lab", "faculty")

PLACEHOLDERS: tuple[CommandSpec, ...] = (
    *LOAD_SPECS,
    *SAVE_SPECS,
    *PRINT_SPECS,
    CommandSpec(
        "add",
        positionals=(Positional("kind", choices=KINDS), Positional("id")),
        description="Add a course, room, lab, or faculty member",
    ),
    *MODIFY_SPECS,
    *DELETE_SPECS,
    *RUN_SPECS,
    *SCHEDULES_SPECS,
    *DISPLAY_SPECS,
)

PROMPT = "> "
GOODBYE = "Goodbye."


def _quit(console: Console, session: Session, invocation: Invocation) -> None:
    raise QuitShell


QUIT = CommandSpec("quit", description="Leave the shell", handler=_quit)
EXIT = CommandSpec("exit", description="Same as quit", handler=_quit)


def build_registry(specs: Iterable[CommandSpec] = PLACEHOLDERS) -> Registry:
    """Feature specs plus the shell's own ``help``, ``quit``, and ``exit``."""
    registry = Registry(specs)
    registry.register(help_spec(registry), QUIT, EXIT)
    return registry


def show_commands(console: Console, registry: Registry) -> None:
    console.say("")
    console.say("Commands:")
    for line in format_help(registry):
        console.say(line)
    console.say("")


def run(console: Console, session: Session, registry: Registry | None = None) -> None:
    """Read and evaluate commands until quit. Ctrl-C or Ctrl-D inside a command returns here."""
    registry = registry if registry is not None else build_registry()
    welcome(console)
    show_commands(console, registry)
    while True:
        try:
            line = console.ask(PROMPT)
        except (EOFError, KeyboardInterrupt):
            console.say("")
            return
        if not line.strip():
            continue
        try:
            evaluate(console, session, line, registry)
        except QuitShell:
            console.say(GOODBYE)
            return
        except UnknownCommand:
            console.say(INVALID_CHOICE)
            show_commands(console, registry)
        except CommandError as exc:
            console.say(str(exc))
        except (EOFError, KeyboardInterrupt):
            console.say("")


def main() -> None:
    quiet_library_logging()
    run(StdConsole(), Session())


if __name__ == "__main__":
    main()
