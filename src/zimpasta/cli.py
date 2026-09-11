"""Shell entry point: welcome page, main menu, dispatch.

To wire in your feature, add your command function under ``zimpasta/commands/`` and
replace your line in ``MENU``.
"""

from zimpasta.commands import Command, not_implemented
from zimpasta.commands.results import manage_results
from zimpasta.commands.run import run_schedule
from zimpasta.console import Console, StdConsole
from zimpasta.generate import quiet_library_logging
from zimpasta.prompts import ask_menu
from zimpasta.session import Session
from zimpasta.welcome_page import welcome

MENU: tuple[tuple[str, Command], ...] = (
    ("Load config file", not_implemented("Load config file")),
    ("Add", not_implemented("Add")),
    ("Modify", not_implemented("Modify")),
    ("Delete", not_implemented("Delete")),
    ("Run Schedule", run_schedule),
    ("Generated schedules", manage_results),
    ("Display schedules", not_implemented("Display schedules")),
)
"""Main-menu label and command for each feature, in display order. Quit is appended."""

QUIT_LABEL = "Quit"
GOODBYE = "Goodbye."


def run(console: Console, session: Session) -> None:
    """Show the menu until the user quits. Ctrl-C or Ctrl-D inside a command returns here."""
    welcome(console)
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
    quiet_library_logging()
    run(StdConsole(), Session())


if __name__ == "__main__":
    main()
