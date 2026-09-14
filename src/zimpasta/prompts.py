"""Validated console prompts shared by every command.

Each helper loops until it gets acceptable input, so no invalid answer can end the
session. Message strings fixed by the acceptance scenarios are module constants; use
them rather than retyping the text.
"""

from collections.abc import Sequence

from zimpasta.console import Console

INVALID_CHOICE = "Invalid choice."
NON_NUMERIC = "Please enter numerical characters only."
INVALID_YES_NO = "Invalid option. Please choose yes or no."

MENU_PROMPT = "Choose an option: "

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
