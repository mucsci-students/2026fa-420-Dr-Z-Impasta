"File: Welomce_page"

"Author: Mohamed Mussa"

"""Welcome page shown at startup, before the main menu."""

from zimpasta.console import Console


def welcome(console: Console) -> None:
    console.say("\n" * 5)
    console.say("SCHEDULE GENERATOR".center(50))
    console.say("=" * 50)
    console.say("")
    console.say("Welcome to the Schedule Generator!".center(50))
    console.say("\n" * 5)
