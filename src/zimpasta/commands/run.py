"""The "Run Schedule" command.

Flow (matching the acceptance scenarios): choose the config file, enter the maximum
number of schedules, choose whether to optimize, choose ``csv`` or ``Json``, enter an
output file name, generate, then write and report the output location. Every invalid
answer re-prompts; nothing here can end the session.
"""

import json
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.commands.export_flow import export_with_prompts
from zimpasta.config_loader import load_config
from zimpasta.console import Console
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
from zimpasta.prompts import ask_format, ask_int, ask_output_path, ask_yes_no
from zimpasta.session import Session

CONFIG_PROMPT = "Config file to use [{default}]: "
LIMIT_PROMPT = "Maximum number of schedules [{default}]: "
OPTIMIZE_PROMPT = "Optimize? (yes/no): "
FORMAT_PROMPT = "Output format (csv/Json): "

CANCELLED = "Run cancelled."

_NO_FEASIBLE_TEXT = {
    REASON_EXHAUSTED: "No feasible schedule exists for this configuration.",
    REASON_TIMEOUT: "The solver timed out before finding a schedule. Try a simpler configuration.",
    REASON_UNKNOWN: "The solver could not determine whether a feasible schedule exists.",
}

ConfigLoader = Callable[[Path], CombinedConfig]
Generator = Callable[..., GenerationOutcome]


def run_schedule(
    console: Console,
    session: Session,
    *,
    loader: ConfigLoader = load_config,
    generator: Generator = generate_schedules,
) -> None:
    """Interactively generate schedules and export them.

    ``loader`` and ``generator`` are injection points for tests and for the config-loading
    feature; the defaults are the real implementations.
    """
    try:
        _run(console, session, loader, generator)
    except (EOFError, KeyboardInterrupt):
        console.say("")
        console.say(CANCELLED)


def _run(console: Console, session: Session, loader: ConfigLoader, generator: Generator) -> None:
    config = _choose_config(console, session, loader)
    limit = ask_int(console, LIMIT_PROMPT.format(default=config.limit), default=config.limit)
    optimize = ask_yes_no(console, OPTIMIZE_PROMPT)
    fmt = ask_format(console, FORMAT_PROMPT)
    target = ask_output_path(console, fmt)

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
            export_with_prompts(console, result.schedules, fmt, target)


def _choose_config(console: Console, session: Session, loader: ConfigLoader) -> CombinedConfig:
    """Ask which config file to use. Enter keeps the session's current configuration.

    The session is only updated after a successful load, so a bad path or an invalid
    file leaves the previously valid configuration intact.
    """
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
                return session.config
            console.say("No configuration is loaded. Enter the path to a config file.")
            continue

        path = Path(raw).expanduser()
        try:
            config = loader(path)
        except OSError as exc:
            console.say(f"Cannot read config file '{path}': {exc.strerror or exc}")
            continue
        except json.JSONDecodeError as exc:
            console.say(f"Config file '{path}' is not valid JSON: {exc}")
            continue
        except ValidationError as exc:
            console.say(f"Config file '{path}' is not a valid configuration:")
            for line in format_validation_errors(exc):
                console.say(f"  - {line}")
            continue

        session.config = config
        session.config_path = path.resolve()
        return config


def _success_text(result: GenerationResult) -> str:
    if result.reached_limit:
        return f"Generated {result.count} schedule(s)."
    return (
        f"Generated {result.count} of {result.limit} requested schedule(s); "
        f"{describe_reason(result.completion_reason)}."
    )
