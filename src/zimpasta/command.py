"""Command model and the master evaluator.

Every action in the shell is a command line such as ``modify course "CS 101" name``.
The REPL hands each line to :func:`evaluate`, which tokenizes it, finds the matching
:class:`CommandSpec` in a :class:`Registry`, parses positionals and ``--options``, asks
the spec's *builder* to prompt for any required value that is missing, and finally calls
the spec's *handler*. A complete command line therefore runs straight away, while a bare
verb engages the same interactive prompts the menu used to, and both paths execute
through this one function.
"""

import shlex
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field

from zimpasta.console import Console
from zimpasta.prompts import ask_choice
from zimpasta.session import Session

NOT_IMPLEMENTED = "{name} is not implemented yet."
RUNNING = "Running: {line}"


class CommandError(Exception):
    """A command line that cannot run. The message is shown to the user as-is."""


class UnknownCommand(CommandError):
    """The first word matches no registered command."""


class QuitShell(Exception):
    """Raised by the quit command; the REPL catches it and exits."""


@dataclass(frozen=True)
class Positional:
    """One positional argument. ``choices`` (lowercase) restricts and normalizes the value."""

    name: str
    required: bool = True
    choices: tuple[str, ...] = ()
    help: str = ""

    @property
    def usage(self) -> str:
        inner = "|".join(self.choices) if self.choices else self.name
        return f"<{inner}>" if self.required else f"[<{inner}>]"


@dataclass(frozen=True)
class Option:
    """One ``--name value`` option, or a bare ``--name`` flag when ``flag`` is true."""

    name: str
    required: bool = False
    choices: tuple[str, ...] = ()
    flag: bool = False
    help: str = ""

    @property
    def usage(self) -> str:
        if self.flag:
            text = f"--{self.name}"
        else:
            value = "|".join(self.choices) if self.choices else self.name.upper()
            text = f"--{self.name} {value}"
        return text if self.required else f"[{text}]"


@dataclass(frozen=True)
class Invocation:
    """A parsed command: the spec plus whichever positionals and options were given."""

    spec: "CommandSpec"
    positionals: dict[str, str] = field(default_factory=dict)
    options: dict[str, str | bool] = field(default_factory=dict)

    def get(self, name: str, default: str | bool | None = None) -> str | bool | None:
        """Value of a positional or option by name, or ``default`` when absent."""
        if name in self.positionals:
            return self.positionals[name]
        return self.options.get(name, default)

    def missing(self) -> tuple[str, ...]:
        """Names of required positionals and options that were not given."""
        names = [
            p.name for p in self.spec.positionals if p.required and p.name not in self.positionals
        ]
        names += [
            f"--{o.name}" for o in self.spec.options if o.required and o.name not in self.options
        ]
        return tuple(names)

    """"""

    def check_for_choices(self, pos: Positional) -> tuple:
        """Checks if a Positional has a choices attribute and returns the choices tuple, if so

        If not, an empty tuple if returned
        """
        if hasattr(pos, "choices"):
            return pos.choices
        return ()

    def missing_with_choices(self) -> tuple[str, ...]:
        """Names of required positionals, their choices, and options that were not given."""
        names = [
            (p.name + ": " + str(", ".join(self.check_for_choices(p))))
            for p in self.spec.positionals
            if p.required and p.name not in self.positionals
        ]
        names += [
            f"--{o.name}" for o in self.spec.options if o.required and o.name not in self.options
        ]
        return tuple(names)

    """"""

    @property
    def complete(self) -> bool:
        return not self.missing()

    def with_values(
        self,
        positionals: dict[str, str] | None = None,
        options: dict[str, str | bool] | None = None,
    ) -> "Invocation":
        """A copy with extra values filled in; builders use this to complete a command."""
        return Invocation(
            self.spec,
            {**self.positionals, **(positionals or {})},
            {**self.options, **(options or {})},
        )

    def to_tokens(self) -> list[str]:
        tokens = [self.spec.verb]
        if self.spec.noun:
            tokens.append(self.spec.noun)
        for positional in self.spec.positionals:
            if positional.name in self.positionals:
                tokens.append(self.positionals[positional.name])
        for option in self.spec.options:
            if option.name not in self.options:
                continue
            value = self.options[option.name]
            if option.flag:
                if value:
                    tokens.append(f"--{option.name}")
            else:
                tokens.extend([f"--{option.name}", str(value)])
        return tokens

    def to_line(self) -> str:
        """The command line that would reproduce this invocation, quoted for the shell."""
        return shlex.join(self.to_tokens())


Handler = Callable[[Console, Session, Invocation], None]
"""Does the work for a complete invocation. Never prompts for arguments."""

Builder = Callable[[Console, Session, Invocation], "Invocation | None"]
"""Prompts for whatever a partial invocation lacks; returns ``None`` when the user cancels."""


@dataclass(frozen=True)
class CommandSpec:
    """One command: its grammar, its handler, and its interactive builder.

    ``handler`` may be ``None`` for a placeholder that has not been implemented yet.
    """

    verb: str
    noun: str | None = None
    positionals: tuple[Positional, ...] = ()
    options: tuple[Option, ...] = ()
    description: str = ""
    handler: Handler | None = None
    builder: Builder | None = None

    @property
    def name(self) -> str:
        return f"{self.verb} {self.noun}" if self.noun else self.verb

    @property
    def usage(self) -> str:
        parts = [self.name]
        parts.extend(p.usage for p in self.positionals)
        parts.extend(o.usage for o in self.options)
        return " ".join(parts)

    @property
    def implemented(self) -> bool:
        return self.handler is not None

    def parse(self, tokens: Sequence[str]) -> Invocation:
        """Parse the tokens that follow the verb and noun.

        Raises:
            CommandError: unknown option, missing option value, too many positionals,
                or a value outside its declared choices.
        """
        positionals: dict[str, str] = {}
        options: dict[str, str | bool] = {}
        by_name = {o.name: o for o in self.options}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token.startswith("--") and len(token) > 2:
                name, has_inline, inline = token[2:].partition("=")
                option = by_name.get(name.lower())
                if option is None:
                    raise CommandError(f"Unknown option --{name}. Usage: {self.usage}")
                if option.flag:
                    if has_inline:
                        raise CommandError(f"--{option.name} takes no value. Usage: {self.usage}")
                    options[option.name] = True
                    continue
                if has_inline:
                    value = inline
                elif index < len(tokens):
                    value = tokens[index]
                    index += 1
                else:
                    raise CommandError(f"--{option.name} needs a value. Usage: {self.usage}")
                options[option.name] = _checked(f"--{option.name}", value, option.choices)
            else:
                position = len(positionals)
                if position >= len(self.positionals):
                    raise CommandError(f"Too many arguments. Usage: {self.usage}")
                positional = self.positionals[position]
                positionals[positional.name] = _checked(positional.name, token, positional.choices)
        return Invocation(self, positionals, options)


def _checked(label: str, value: str, choices: tuple[str, ...]) -> str:
    if not choices:
        return value
    lowered = value.lower()
    if lowered in choices:
        return lowered
    raise CommandError(f"{label} must be one of: {', '.join(choices)}.")


class Registry:
    """The commands the shell knows, keyed by verb and optional noun."""

    def __init__(self, specs: Iterable[CommandSpec] = ()) -> None:
        self._specs: dict[tuple[str, str | None], CommandSpec] = {}
        self.register(*specs)

    def register(self, *specs: CommandSpec) -> None:
        for spec in specs:
            key = (spec.verb.lower(), spec.noun.lower() if spec.noun else None)
            if key in self._specs:
                raise ValueError(f"Command already registered: {spec.name}")
            self._specs[key] = spec

    def __iter__(self) -> Iterator[CommandSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    def for_verb(self, verb: str) -> list[CommandSpec]:
        wanted = verb.lower()
        return [spec for (v, _), spec in self._specs.items() if v == wanted]

    def resolve(
        self, tokens: Sequence[str], console: Console | None = None
    ) -> tuple[CommandSpec, list[str]]:
        """Pick the spec for a token list and return it with the tokens that follow it.

        A verb with several nouns and no noun given asks the user which one, through
        ``console``, so that a bare verb still leads into an interactive flow.

        Raises:
            UnknownCommand: the verb is not registered.
            CommandError: the noun is wrong, or missing with no console to ask through.
        """
        if not tokens:
            raise CommandError("Type a command, or help to list them.")
        verb = tokens[0].lower()
        candidates = self.for_verb(verb)
        if not candidates:
            raise UnknownCommand(f"Unknown command: {tokens[0]}")
        direct = next((spec for spec in candidates if spec.noun is None), None)
        if direct is not None:
            return direct, list(tokens[1:])

        nouns = [spec.noun.lower() for spec in candidates if spec.noun]
        if len(tokens) > 1 and tokens[1].lower() in nouns:
            spec = candidates[nouns.index(tokens[1].lower())]
            return spec, list(tokens[2:])
        if len(candidates) == 1:
            return candidates[0], list(tokens[1:])
        listing = ", ".join(nouns)
        if len(tokens) > 1 or console is None:
            raise CommandError(f"'{verb}' needs one of: {listing}.")
        chosen = ask_choice(console, f"{verb} what? ({'/'.join(nouns)}): ", nouns)
        return candidates[nouns.index(chosen)], []


def tokenize(line: str) -> list[str]:
    """Split a command line the way a shell would, so ``"CS 101"`` stays one token.

    Single and double quotes group words. Backslashes are ordinary characters, not
    escapes, so Windows paths such as ``C:\\Users\\me\\config.json`` need no quoting and
    the lines produced by :meth:`Invocation.to_line` parse back to the same tokens on
    every platform.
    """
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    try:
        return list(lexer)
    except ValueError as exc:
        raise CommandError(f"Cannot parse that command: {exc}.") from None


def evaluate(
    console: Console,
    session: Session,
    line: str | Sequence[str],
    registry: Registry,
) -> None:
    """Run one command line: resolve, parse, complete through the builder, then handle.

    Raises:
        CommandError: the line cannot be turned into a runnable command.
        QuitShell: the quit command was run.
    """
    tokens = tokenize(line) if isinstance(line, str) else list(line)
    spec, rest = registry.resolve(tokens, console)
    if not spec.implemented:
        console.say(NOT_IMPLEMENTED.format(name=spec.name))
        return
    invocation = spec.parse(rest)
    if not invocation.complete:
        if spec.builder is None:
            missing = ", ".join(invocation.missing())
            raise CommandError(f"Missing {missing}. Usage: {spec.usage}")
        built = spec.builder(console, session, invocation)
        if built is None:
            return
        if not built.complete:
            missing = ", ".join(built.missing())
            raise CommandError(f"Still missing {missing}. Usage: {spec.usage}")
        console.say(RUNNING.format(line=built.to_line()))
        invocation = built
    assert spec.handler is not None
    spec.handler(console, session, invocation)
