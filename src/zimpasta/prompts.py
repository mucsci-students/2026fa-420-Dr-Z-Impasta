"""Validated console prompts shared by every command.

Each helper loops until it gets acceptable input, so no invalid answer can end the
session. Message strings fixed by the acceptance scenarios are module constants; use
them rather than retyping the text.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from zimpasta.console import Console

CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_config.json"

INVALID_CHOICE = "Invalid choice."
NON_NUMERIC = "Please enter numerical characters only."
INVALID_YES_NO = "Invalid option. Please choose yes or no."
INVALID_ROOM_CHOICE = "Invalid choice. Please enter a valid room name."

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


def ask_room(console: Console, prompt: str) -> bool:
    """Prompts the user about a room and returns a bool value if that room exist
    in the config file.

    Any entry that is not a value for the "name" keys in the "rooms" json object
    will print 'Invalid choice. Please enter a valid room name.' and reprompt the user
    """
    with open(CONFIG_FILE) as file:
        config = json.load(file)

    while True:
        raw = console.ask(prompt).strip()
        if any(room["name"] == raw for room in config["config"]["rooms"]):
            return True
        else:
            console.say(INVALID_ROOM_CHOICE + "\n")

    return False
