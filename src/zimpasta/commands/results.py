"""The "Generated schedules" command: summary, inspect, export, clear."""

from zimpasta.commands.export_flow import export_with_prompts
from zimpasta.console import Console
from zimpasta.prompts import ask_format, ask_int, ask_menu, ask_output_path
from zimpasta.results import ScheduleStore
from zimpasta.session import Session
from zimpasta.view import format_schedule, summarize

RESULTS_MENU = ("View summary", "Inspect a schedule", "Export schedules", "Clear results", "Back")
EXPORT_MENU = ("All schedules", "One schedule", "Back")

NO_RESULTS = "No generated schedules in this session. Run the scheduler first."
CLEARED = "Cleared generated schedules."
FORMAT_PROMPT = "Output format (csv/Json): "


def manage_results(console: Console, session: Session) -> None:
    """Loop over the results menu until the user goes back or clears the results."""
    try:
        _manage(console, session)
    except (EOFError, KeyboardInterrupt):
        console.say("")


def _manage(console: Console, session: Session) -> None:
    store = session.results
    while True:
        if store.is_empty():
            console.say(NO_RESULTS)
            return
        choice = ask_menu(console, "Generated schedules", RESULTS_MENU)
        if choice == 1:
            console.say(summarize(store.result))
        elif choice == 2:
            number = _ask_schedule_number(console, store)
            console.say(format_schedule(store.get(number), number=number))
        elif choice == 3:
            _export(console, store)
        elif choice == 4:
            store.clear()
            console.say(CLEARED)
            return
        else:
            return


def _export(console: Console, store: ScheduleStore) -> None:
    which = ask_menu(console, "Export", EXPORT_MENU)
    if which == 3:
        return
    if which == 1:
        schedules = store.schedules
    else:
        schedules = [store.get(_ask_schedule_number(console, store))]
    fmt = ask_format(console, FORMAT_PROMPT)
    target = ask_output_path(console, fmt)
    export_with_prompts(console, schedules, fmt, target)


def _ask_schedule_number(console: Console, store: ScheduleStore) -> int:
    return ask_int(console, f"Schedule number (1-{len(store)}): ", minimum=1, maximum=len(store))
