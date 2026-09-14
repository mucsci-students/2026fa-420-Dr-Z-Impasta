from tests.helpers import ScriptedConsole
from zimpasta.prompts import (
    INVALID_CHOICE,
    INVALID_YES_NO,
    MENU_PROMPT,
    NON_NUMERIC,
    ask_choice,
    ask_int,
    ask_menu,
    ask_yes_no,
)


def test_ask_int_reprompts_on_non_numeric_input():
    console = ScriptedConsole(["abc", "3.5", "-1", "7"])

    assert ask_int(console, "Limit: ") == 7
    assert console.output == [NON_NUMERIC, NON_NUMERIC, NON_NUMERIC]
    assert console.prompts == ["Limit: "] * 4


def test_ask_int_uses_default_on_blank_and_enforces_range():
    assert ask_int(ScriptedConsole([""]), "Limit: ", default=10) == 10

    console = ScriptedConsole(["", "0", "2"])
    assert ask_int(console, "Limit: ") == 2
    assert console.output == [NON_NUMERIC, "Please enter a number of 1 or more."]

    console = ScriptedConsole(["9", "3"])
    assert ask_int(console, "Number: ", minimum=1, maximum=3) == 3
    assert console.output == ["Please enter a number between 1 and 3."]


def test_ask_yes_no_reprompts_until_valid():
    console = ScriptedConsole(["maybe", "", "YES"])

    assert ask_yes_no(console, "Optimize? (yes/no): ") is True
    assert console.output == [INVALID_YES_NO, INVALID_YES_NO]

    assert ask_yes_no(ScriptedConsole(["n"]), "? ") is False
    assert ask_yes_no(ScriptedConsole([" No "]), "? ") is False
    assert ask_yes_no(ScriptedConsole(["y"]), "? ") is True


def test_ask_menu_redisplays_after_invalid_choice():
    console = ScriptedConsole(["9", "x", "2"])

    assert ask_menu(console, "Main menu", ["Run Schedule", "Quit"]) == 2
    assert console.output.count(INVALID_CHOICE) == 2
    assert console.output.count("  1) Run Schedule") == 3
    assert console.prompts == [MENU_PROMPT] * 3


def test_ask_choice_accepts_name_or_number_and_reprompts():
    console = ScriptedConsole(["truck", "0", "Room"])
    assert ask_choice(console, "Kind: ", ("course", "room")) == "room"
    assert console.output.count(INVALID_CHOICE) == 2
    assert "Choose one of: course, room" in console.output

    assert ask_choice(ScriptedConsole(["2"]), "Kind: ", ("course", "room")) == "room"
