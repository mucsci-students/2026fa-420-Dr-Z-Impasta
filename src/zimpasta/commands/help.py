"""The ``help`` command: list every command, or one verb's commands."""

from collections.abc import Iterable

from zimpasta.command import CommandError, CommandSpec, Invocation, Positional, Registry
from zimpasta.console import Console
from zimpasta.session import Session

COLUMN = 44
"""Usage strings up to this width get their description on the same line."""


def format_help(specs: Iterable[CommandSpec]) -> list[str]:
    """One ``usage  description`` line per spec; long usages put the description below."""
    specs = list(specs)
    if not specs:
        return []
    width = min(max(len(spec.usage) for spec in specs), COLUMN)
    lines = []
    for spec in specs:
        if len(spec.usage) <= width:
            lines.append(f"  {spec.usage.ljust(width)}  {spec.description}".rstrip())
        else:
            lines.append(f"  {spec.usage}")
            if spec.description:
                lines.append(f"  {' ' * width}  {spec.description}")
    return lines


def help_spec(registry: Registry) -> CommandSpec:
    """Build the help command over ``registry`` (it must see later registrations too)."""

    def handler(console: Console, session: Session, invocation: Invocation) -> None:
        verb = invocation.get("command")
        specs = registry.for_verb(str(verb)) if verb else list(registry)
        if verb and not specs:
            raise CommandError(f"Unknown command: {verb}")
        for line in format_help(specs):
            console.say(line)

    return CommandSpec(
        "help",
        positionals=(Positional("command", required=False, help="show one command"),),
        description="List commands, or show one",
        handler=handler,
    )
