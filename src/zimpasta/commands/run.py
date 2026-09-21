"""The ``run schedule`` command.

Usage: ``run schedule [--config PATH] --limit N --optimize yes|no --format csv|json
--output FILE [--overwrite]``. A complete command line runs straight away. ``run`` alone,
or a line missing any of the required options, goes through the builder, which asks the
acceptance-scenario prompts (config file, maximum number of schedules, optimize, format,
output file name) for whatever was left out and then runs the same command. Every invalid
answer re-prompts; nothing here can end the session.
"""

import json
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.command import CommandError, CommandSpec, Invocation, Option
from zimpasta.commands.export_flow import export_with_prompts
from zimpasta.config_loader import load_config
from zimpasta.console import Console
from zimpasta.export import ExportFormat, resolve_output_path
from zimpasta.generate import (
    REASON_EXHAUSTED,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    GenerationFailed,
    GenerationOutcome,
    GenerationResult,
    GenerationSuccess,
    InvalidConfiguration,
    NoFeasibleSchedule,
    describe_reason,
    format_validation_errors,
    generate_schedules,
)
from zimpasta.prompts import OutputTarget, ask_format, ask_int, ask_output_path, ask_yes_no
from zimpasta.session import Session

CONFIG_PROMPT = "Config file to use [{default}]: "
LIMIT_PROMPT = "Maximum number of schedules [{default}]: "
OPTIMIZE_PROMPT = "Optimize? (yes/no): "
FORMAT_PROMPT = "Output format (csv/Json): "

CANCELLED = "Run cancelled."
NO_CONFIG = "No configuration is loaded. Pass --config PATH, or load one first."
NO_CONFIG_PROMPT = "No configuration is loaded. Enter the path to a config file."
BAD_LIMIT = "--limit must be a whole number of 1 or more."

FORMATS = tuple(fmt.value for fmt in ExportFormat)
YES_NO = ("yes", "no")

_NO_FEASIBLE_TEXT = {
    REASON_EXHAUSTED: "No feasible schedule exists for this configuration.",
    REASON_TIMEOUT: "The solver timed out before finding a schedule. Try a simpler configuration.",
    REASON_UNKNOWN: "The solver could not determine whether a feasible schedule exists.",
}

ConfigLoader = Callable[[Path], CombinedConfig]
Generator = Callable[..., GenerationOutcome]


def make_specs(
    *,
    loader: ConfigLoader = load_config,
    generator: Generator = generate_schedules,
) -> tuple[CommandSpec, ...]:
    """The run commands. ``loader`` and ``generator`` are injection points for tests."""

    def handler(console: Console, session: Session, invocation: Invocation) -> None:
        run_schedule(console, session, invocation, loader=loader, generator=generator)

    def builder(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
        return build_run_schedule(console, session, invocation, loader=loader)

    return (
        CommandSpec(
            "run",
            "schedule",
            options=(
                Option("config", help="configuration file; defaults to the loaded one"),
                Option("limit", required=True, help="maximum number of schedules"),
                Option("optimize", required=True, choices=YES_NO),
                Option("format", required=True, choices=FORMATS),
                Option("output", required=True, help="output file; the extension is added"),
                Option("overwrite", flag=True, help="replace an existing output file"),
            ),
            description="Generate schedules and export them",
            handler=handler,
            builder=builder,
        ),
    )


SPECS = make_specs()


def run_schedule(
    console: Console,
    session: Session,
    invocation: Invocation,
    *,
    loader: ConfigLoader = load_config,
    generator: Generator = generate_schedules,
) -> None:
    """Handler: generate schedules from the given or loaded configuration and export them.

    Raises:
        CommandError: no configuration, an unreadable or invalid ``--config`` file, or a
            ``--limit`` that is not a positive whole number. Generation outcomes are
            reported on the console, never raised.
    """
    config = _config_for(session, invocation, loader)
    limit = _limit(invocation)
    optimize = invocation.get("optimize") == "yes"
    fmt = ExportFormat(str(invocation.get("format")))
    target = OutputTarget(
        resolve_output_path(str(invocation.get("output")), fmt),
        overwrite=bool(invocation.get("overwrite", False)),
    )

    mode = "with optimization" if optimize else "without optimization"
    console.say(f"Generating up to {limit} schedule(s) {mode}...")
    outcome = generator(
        config,
        limit=limit,
        optimize=optimize,
        config_path=session.config_path,
        on_progress=lambda found, total: console.say(f"  schedule {found} of {total} found"),
    )

    match outcome:
        case InvalidConfiguration(errors=errors):
            console.say("Invalid configuration. Nothing was generated.")
            for error in errors:
                console.say(f"  - {error}")
        case NoFeasibleSchedule(reason=reason):
            console.say(_NO_FEASIBLE_TEXT.get(reason, _NO_FEASIBLE_TEXT[REASON_UNKNOWN]))
            console.say(f"Nothing was written to {target.path}.")
        case GenerationFailed(message=message):
            console.say(f"Unexpected error while generating schedules: {message}")
            console.say("The configuration and any previous results are unchanged.")
        case GenerationSuccess(result=result):
            session.results.replace(result)
            console.say(_success_text(result))
            exported = export_with_prompts(console, result.schedules, fmt, target)
            session.schedule_path = exported.path


def build_run_schedule(
    console: Console,
    session: Session,
    invocation: Invocation,
    *,
    loader: ConfigLoader = load_config,
) -> Invocation | None:
    """Builder: ask, in scenario order, for each required value the command line left out.

    The config prompt is asked for a bare ``run`` or when no configuration is loaded;
    a partial command with a loaded configuration keeps using it. A ``--config`` given on
    the command line is loaded first so the limit prompt can default to that file's limit.
    Ctrl-C or Ctrl-D cancels the run.
    """
    try:
        options: dict[str, str | bool] = {}
        given = invocation.get("config")
        if given is None:
            if not invocation.options or session.config is None:
                chosen = _choose_config(console, session, loader)
                if chosen is not None:
                    options["config"] = chosen
        else:
            problem = load_into_session(session, Path(str(given)).expanduser(), loader)
            if problem is not None:
                raise CommandError(problem)
        config = session.config
        assert config is not None

        if invocation.get("limit") is None:
            prompt = LIMIT_PROMPT.format(default=config.limit)
            options["limit"] = str(ask_int(console, prompt, default=config.limit))
        if invocation.get("optimize") is None:
            options["optimize"] = "yes" if ask_yes_no(console, OPTIMIZE_PROMPT) else "no"
        given_format = invocation.get("format")
        if given_format is None:
            fmt = ask_format(console, FORMAT_PROMPT)
            options["format"] = fmt.value
        else:
            fmt = ExportFormat(str(given_format))
        if invocation.get("output") is None:
            target = ask_output_path(console, fmt)
            options["output"] = str(target.path)
            if target.overwrite:
                options["overwrite"] = True
        return invocation.with_values(options=options)
    except (EOFError, KeyboardInterrupt):
        console.say("")
        console.say(CANCELLED)
        return None


def load_into_session(session: Session, path: Path, loader: ConfigLoader) -> str | None:
    """Load ``path`` into the session. Returns a message when it cannot be, else ``None``.

    The session is only updated after a successful load, so a bad path or an invalid file
    leaves the previously valid configuration intact.
    """
    try:
        config = loader(path)
    except OSError as exc:
        return f"Cannot read config file '{path}': {exc.strerror or exc}"
    except json.JSONDecodeError as exc:
        return f"Config file '{path}' is not valid JSON: {exc}"
    except ValidationError as exc:
        lines = [f"Config file '{path}' is not a valid configuration:"]
        lines.extend(f"  - {line}" for line in format_validation_errors(exc))
        return "\n".join(lines)
    session.config = config
    session.config_path = path.resolve()
    return None


def _config_for(session: Session, invocation: Invocation, loader: ConfigLoader) -> CombinedConfig:
    given = invocation.get("config")
    if given is None:
        if session.config is None:
            raise CommandError(NO_CONFIG)
        return session.config
    problem = load_into_session(session, Path(str(given)).expanduser(), loader)
    if problem is not None:
        raise CommandError(problem)
    assert session.config is not None
    return session.config


def _limit(invocation: Invocation) -> int:
    raw = str(invocation.get("limit")).strip()
    if not raw.isdecimal() or int(raw) < 1:
        raise CommandError(BAD_LIMIT)
    return int(raw)


def _choose_config(console: Console, session: Session, loader: ConfigLoader) -> str | None:
    """Ask which config file to use. Returns the typed path, or ``None`` to keep the loaded one."""
    while True:
        if session.config_path is not None:
            default = str(session.config_path)
        elif session.config is not None:
            default = "current configuration"
        else:
            default = "none"
        raw = console.ask(CONFIG_PROMPT.format(default=default)).strip()
        if not raw:
            if session.config is not None:
                return None
            console.say(NO_CONFIG_PROMPT)
            continue
        problem = load_into_session(session, Path(raw).expanduser(), loader)
        if problem is not None:
            for line in problem.splitlines():
                console.say(line)
            continue
        return raw


def _success_text(result: GenerationResult) -> str:
    if result.reached_limit:
        return f"Generated {result.count} schedule(s)."
    return (
        f"Generated {result.count} of {result.limit} requested schedule(s); "
        f"{describe_reason(result.completion_reason)}."
    )
