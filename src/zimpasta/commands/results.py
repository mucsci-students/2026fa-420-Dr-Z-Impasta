"""The ``schedules`` commands: summary, show, export, clear.

They work on the schedules kept in ``session.results`` by the most recent successful
``run schedule``. ``schedules show`` and ``schedules export`` have builders, so typing
them bare asks for the schedule number, format, and output file.
"""

from zimpasta.command import CommandError, CommandSpec, Invocation, Option, Positional
from zimpasta.commands.export_flow import export_with_prompts
from zimpasta.console import Console
from zimpasta.export import ExportFormat, resolve_output_path
from zimpasta.prompts import OutputTarget, ask_format, ask_int, ask_output_path
from zimpasta.results import ScheduleStore
from zimpasta.session import Session
from zimpasta.view import format_schedule, summarize

NO_RESULTS = "No generated schedules in this session. Run the scheduler first."
CLEARED = "Cleared generated schedules."
FORMAT_PROMPT = "Output format (csv/Json): "
WHICH_PROMPT = "Export which (all, or 1-{count}): "
BAD_WHICH = "Please enter all or a number between 1 and {count}."

FORMATS = tuple(fmt.value for fmt in ExportFormat)


def summary(console: Console, session: Session, invocation: Invocation) -> None:
    store = _results(console, session)
    if store is not None and store.result is not None:
        console.say(summarize(store.result))


def show(console: Console, session: Session, invocation: Invocation) -> None:
    store = _results(console, session)
    if store is None:
        return
    number = _number(str(invocation.get("number")), len(store))
    console.say(format_schedule(store.get(number), number=number))


def build_show(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    store = _results(console, session)
    if store is None:
        return None
    return invocation.with_values({"number": str(_ask_number(console, store))})


def export(console: Console, session: Session, invocation: Invocation) -> None:
    store = _results(console, session)
    if store is None:
        return
    which = str(invocation.get("which")).strip().lower()
    if which == "all":
        schedules = store.schedules
    else:
        schedules = [store.get(_number(which, len(store)))]
    fmt = ExportFormat(str(invocation.get("format")))
    target = OutputTarget(
        resolve_output_path(str(invocation.get("output")), fmt),
        overwrite=bool(invocation.get("overwrite", False)),
    )
    result = export_with_prompts(console, schedules, fmt, target)
    session.schedule_path = result.path


def build_export(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    store = _results(console, session)
    if store is None:
        return None
    positionals: dict[str, str] = {}
    options: dict[str, str | bool] = {}
    if invocation.get("which") is None:
        positionals["which"] = _ask_which(console, store)
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
    return invocation.with_values(positionals, options)


def clear(console: Console, session: Session, invocation: Invocation) -> None:
    store = _results(console, session)
    if store is None:
        return
    store.clear()
    console.say(CLEARED)


SPECS = (
    CommandSpec(
        "schedules",
        "summary",
        description="Summarize the generated schedules",
        handler=summary,
    ),
    CommandSpec(
        "schedules",
        "show",
        positionals=(Positional("number"),),
        description="Show one generated schedule",
        handler=show,
        builder=build_show,
    ),
    CommandSpec(
        "schedules",
        "export",
        positionals=(Positional("which", help="a schedule number, or all"),),
        options=(
            Option("format", required=True, choices=FORMATS),
            Option("output", required=True, help="output file; the extension is added"),
            Option("overwrite", flag=True, help="replace an existing output file"),
        ),
        description="Export one schedule or all of them",
        handler=export,
        builder=build_export,
    ),
    CommandSpec(
        "schedules",
        "clear",
        description="Discard the generated schedules",
        handler=clear,
    ),
)


def _results(console: Console, session: Session) -> ScheduleStore | None:
    """The session's results, or ``None`` after telling the user there are none."""
    if session.results.is_empty():
        console.say(NO_RESULTS)
        return None
    return session.results


def _number(raw: str, count: int) -> int:
    raw = raw.strip()
    if not raw.isdecimal() or not 1 <= int(raw) <= count:
        raise CommandError(f"Schedule number must be between 1 and {count}.")
    return int(raw)


def _ask_number(console: Console, store: ScheduleStore) -> int:
    return ask_int(console, f"Schedule number (1-{len(store)}): ", minimum=1, maximum=len(store))


def _ask_which(console: Console, store: ScheduleStore) -> str:
    count = len(store)
    while True:
        raw = console.ask(WHICH_PROMPT.format(count=count)).strip().lower()
        if raw == "all" or (raw.isdecimal() and 1 <= int(raw) <= count):
            return raw
        console.say(BAD_WHICH.format(count=count))
