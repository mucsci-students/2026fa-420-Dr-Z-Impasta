from tests.helpers import ScriptedConsole
from zimpasta.cli import GOODBYE, PLACEHOLDERS, PROMPT, build_registry, run
from zimpasta.command import CommandSpec, Positional
from zimpasta.prompts import INVALID_CHOICE
from zimpasta.session import Session


def test_startup_lists_every_command_then_quit():
    console = ScriptedConsole(["quit"])

    run(console, Session())

    listing = "\n".join(console.output)
    for spec in PLACEHOLDERS:
        assert spec.usage in listing
    assert "help [<command>]" in listing
    assert "quit" in listing
    assert console.prompts == [PROMPT]
    assert console.output[-1] == GOODBYE


def test_unknown_command_prints_invalid_choice_and_the_commands_again():
    console = ScriptedConsole(["frobnicate", "exit"])

    run(console, Session())

    assert console.output.count(INVALID_CHOICE) == 1
    assert console.output.count("Commands:") == 2


def test_command_error_is_printed_and_the_shell_continues():
    console = ScriptedConsole(['modify course "CS 101', "quit"])

    run(console, Session())

    assert any(line.startswith("Cannot parse that command") for line in console.output)
    assert console.output[-1] == GOODBYE


def test_blank_lines_are_ignored():
    console = ScriptedConsole(["", "   ", "quit"])

    run(console, Session())

    assert console.prompts == [PROMPT] * 3
    assert INVALID_CHOICE not in console.output


def test_help_lists_all_and_filters_by_verb():
    console = ScriptedConsole(["help", "help schedules", "help nope", "quit"])

    run(console, Session())

    text = "\n".join(console.output)
    assert "schedules export <which> --format csv|json --output OUTPUT [--overwrite]" in text
    assert "Unknown command: nope" in console.output


def test_full_command_runs_handler_and_bare_verb_uses_builder():
    seen = []

    def handler(console, session, invocation):
        seen.append(invocation.get("id"))

    def builder(console, session, invocation):
        return invocation.with_values({"id": console.ask("Id: ")})

    spec = CommandSpec("greet", positionals=(Positional("id"),), handler=handler, builder=builder)
    registry = build_registry([spec])
    console = ScriptedConsole(['greet "CS 101"', "greet", "CS 102", "quit"])

    run(console, Session(), registry)

    assert seen == ["CS 101", "CS 102"]
    assert "Running: greet 'CS 102'" in console.output


def test_interrupt_inside_a_command_returns_to_the_prompt():
    def interrupted(console, session, invocation):
        raise KeyboardInterrupt

    registry = build_registry([CommandSpec("boom", handler=interrupted)])
    console = ScriptedConsole(["boom", "quit"])

    run(console, Session(), registry)

    assert console.output[-1] == GOODBYE


def test_end_of_input_at_the_prompt_exits_cleanly():
    class EOFConsole(ScriptedConsole):
        def ask(self, prompt):
            raise EOFError

    run(EOFConsole(), Session())
