from tests.helpers import ScriptedConsole
from zimpasta.cli import GOODBYE, MENU, QUIT_LABEL, run
from zimpasta.prompts import INVALID_CHOICE
from zimpasta.session import Session

QUIT = str(len(MENU) + 1)


def test_menu_lists_every_feature_then_quit():
    console = ScriptedConsole([QUIT])

    run(console, Session())

    for number, (label, _) in enumerate(MENU, start=1):
        assert f"  {number}) {label}" in console.output
    assert f"  {QUIT}) {QUIT_LABEL}" in console.output
    assert console.output[-1] == GOODBYE


def test_invalid_choice_redisplays_the_menu():
    console = ScriptedConsole(["0", QUIT])

    run(console, Session())

    assert console.output.count(INVALID_CHOICE) == 1
    assert console.output.count("Main menu") == 2


def test_placeholder_commands_report_not_implemented():
    console = ScriptedConsole(["2", QUIT])

    run(console, Session())

    assert f"{MENU[1][0]} is not implemented yet." in console.output


def test_interrupt_inside_a_command_returns_to_the_menu(monkeypatch):
    def interrupted(console, session):
        raise KeyboardInterrupt

    monkeypatch.setattr("zimpasta.cli.MENU", (("Boom", interrupted),))
    console = ScriptedConsole(["1", "2"])

    run(console, Session())

    assert console.output.count("Main menu") == 2
    assert console.output[-1] == GOODBYE


def test_end_of_input_at_the_menu_exits_cleanly():
    class EOFConsole(ScriptedConsole):
        def ask(self, prompt):
            raise EOFError

    run(EOFConsole(), Session())
