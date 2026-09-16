"""Validated console prompts shared by the commands.

Every prompt loops until it gets acceptable input; none of them can end the session.
Message strings that the acceptance scenarios fix are module constants so tests and
teammates reference one definition.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from zimpasta.console import Console
from zimpasta.export import ExportFormat, resolve_output_path, unwritable_reason

INVALID_CHOICE = "Invalid choice."
NON_NUMERIC = "Please enter numerical characters only."
INVALID_YES_NO = "Invalid option. Please choose yes or no."
UNSUPPORTED_FORMAT = "Unsupported format. Choose csv or Json"
UNWRITABLE_FILENAME = "Cannot make a scheduler to that file name"
VALID_FILENAME_PROMPT = "Type a valid filename."

MENU_PROMPT = "Choose an option: "
OUTPUT_FILE_PROMPT = "Output file name: "

_YES = {"yes", "y"}
_NO = {"no", "n"}


def ask_int(
    console: Console,
    prompt: str,
    *,
    default: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    """Ask for a whole number, re-prompting on anything else.

    An empty answer returns ``default`` when one is given.
    """
    while True:
        raw = console.ask(prompt).strip()
        if not raw and default is not None:
            return default
        if not raw.isdecimal():
            console.say(NON_NUMERIC)
            continue
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            if maximum is None:
                console.say(f"Please enter a number of {minimum} or more.")
            else:
                console.say(f"Please enter a number between {minimum} and {maximum}.")
            continue
        return value


def ask_yes_no(console: Console, prompt: str) -> bool:
    """Accept yes/y/no/n in any case; re-prompt on anything else."""
    while True:
        raw = console.ask(prompt).strip().lower()
        if raw in _YES:
            return True
        if raw in _NO:
            return False
        console.say(INVALID_YES_NO)


def ask_format(console: Console, prompt: str) -> ExportFormat:
    """Accept ``csv`` or ``json`` in any case; re-prompt on anything else."""
    while True:
        fmt = ExportFormat.parse(console.ask(prompt))
        if fmt is not None:
            return fmt
        console.say(UNSUPPORTED_FORMAT)


def ask_menu(console: Console, title: str, options: Sequence[str]) -> int:
    """Display a numbered menu and return the chosen 1-based option.

    Anything that is not a listed number prints ``Invalid choice.`` and shows the menu again.
    """
    while True:
        console.say("")
        console.say(title)
        for number, option in enumerate(options, start=1):
            console.say(f"  {number}) {option}")
        raw = console.ask(MENU_PROMPT).strip()
        if raw.isdecimal() and 1 <= int(raw) <= len(options):
            return int(raw)
        console.say(INVALID_CHOICE)


@dataclass(frozen=True)
class OutputTarget:
    path: Path
    overwrite: bool
    """True when the user has already agreed to replace an existing file at ``path``."""


def ask_output_path(
    console: Console,
    fmt: ExportFormat,
    *,
    prompt: str = OUTPUT_FILE_PROMPT,
    first_prompt: str | None = None,
) -> OutputTarget:
    """Ask for an output file name until it names a writable location.

    An unwritable name prints ``Cannot make a scheduler to that file name`` and re-prompts
    with ``Type a valid filename.``. An existing file asks for overwrite confirmation; a
    ``no`` returns to the file-name prompt.
    """
    next_prompt = first_prompt or prompt
    while True:
        raw = console.ask(next_prompt)
        next_prompt = prompt
        if not raw.strip():
            console.say(UNWRITABLE_FILENAME)
            next_prompt = f"{VALID_FILENAME_PROMPT} "
            continue
        path = resolve_output_path(raw, fmt)
        if unwritable_reason(path) is not None:
            console.say(UNWRITABLE_FILENAME)
            next_prompt = f"{VALID_FILENAME_PROMPT} "
            continue
        if path.exists():
            if not ask_yes_no(console, overwrite_prompt(path)):
                continue
            return OutputTarget(path, overwrite=True)
        return OutputTarget(path, overwrite=False)


def overwrite_prompt(path: Path) -> str:
    return f"File '{path}' already exists. Overwrite? (yes/no): "


def ask_choice(console: Console, prompt: str, choices: Sequence[str]) -> str:
    """Ask for one of ``choices`` by name (any case) or by its 1-based number.

    Anything else prints ``Invalid choice.`` and the list of choices, then asks again.
    """
    lookup = {choice.lower(): choice for choice in choices}
    while True:
        raw = console.ask(prompt).strip()
        if raw.lower() in lookup:
            return lookup[raw.lower()]
        if raw.isdecimal() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        console.say(INVALID_CHOICE)
        console.say("Choose one of: " + ", ".join(choices))
