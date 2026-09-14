"""Shell entry point: banner, main menu, dispatch.

To wire in your feature, add your command function under ``zimpasta/commands/`` and
replace your line in ``MENU``. The welcome-page feature replaces ``banner``.
"""

from zimpasta.commands import Command, not_implemented
from zimpasta.commands.delete import delete
from zimpasta.console import Console, StdConsole
from zimpasta.prompts import ask_menu
from zimpasta.session import Session

MENU: tuple[tuple[str, Command], ...] = (
    ("Load config file", not_implemented("Load config file")),
    ("Add", not_implemented("Add")),
    ("Modify", not_implemented("Modify")),
    ("Delete", delete),
    ("Run Schedule", not_implemented("Run Schedule")),
    ("Display schedules", not_implemented("Display schedules")),
)
"""Main-menu label and command for each feature, in display order. Quit is appended."""

QUIT_LABEL = "Quit"
GOODBYE = "Goodbye."


def banner(console: Console) -> None:
    console.say("Dr. ZImpasta schedule generator")


def run(console: Console, session: Session) -> None:
    """Show the menu until the user quits. Ctrl-C or Ctrl-D inside a command returns here."""
    banner(console)
    labels = [label for label, _ in MENU] + [QUIT_LABEL]
    while True:
        try:
            choice = ask_menu(console, "Main menu", labels)
        except (EOFError, KeyboardInterrupt):
            console.say("")
            return
        if choice == len(labels):
            console.say(GOODBYE)
            return
        _, command = MENU[choice - 1]
        try:
            command(console, session)
        except (EOFError, KeyboardInterrupt):
            console.say("")


def main() -> None:
    run(StdConsole(), Session())


if __name__ == "__main__":
    main()
