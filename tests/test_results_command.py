import json
from datetime import datetime

from tests.helpers import ScriptedConsole
from zimpasta.cli import GOODBYE, MENU, run
from zimpasta.commands.results import CLEARED, NO_RESULTS, manage_results
from zimpasta.commands.run import run_schedule
from zimpasta.generate import GenerationResult
from zimpasta.prompts import INVALID_CHOICE
from zimpasta.session import Session


def session_with(real_schedules) -> Session:
    session = Session()
    session.results.replace(
        GenerationResult(
            schedules=list(real_schedules),
            limit=2,
            optimizer_flags=(),
            completion_reason=None,
            generated_at=datetime(2026, 9, 11, 14, 30),
        )
    )
    return session


def test_results_menu_without_results():
    console = ScriptedConsole()

    manage_results(console, Session())

    assert console.output == [NO_RESULTS]


def test_summary_inspect_and_back(real_schedules):
    console = ScriptedConsole(["1", "2", "9", "2", "5"])

    manage_results(console, session_with(real_schedules))

    assert any(line.startswith("Generated schedules: 2") for line in console.output)
    assert "Please enter a number between 1 and 2." in console.output
    table = next(line for line in console.output if line.startswith("Schedule 2"))
    assert "CS 101.01" in table
    assert "CS 102.01" in table
    assert "(lab)" in table


def test_invalid_choice_redisplays_menu(real_schedules):
    console = ScriptedConsole(["0", "5"])

    manage_results(console, session_with(real_schedules))

    assert console.output.count(INVALID_CHOICE) == 1
    assert console.output.count("  1) View summary") == 2


def test_export_all_and_one(tmp_path, real_schedules):
    console = ScriptedConsole(
        ["3", "1", "json", str(tmp_path / "all"), "3", "2", "2", "csv", str(tmp_path / "one"), "5"]
    )

    manage_results(console, session_with(real_schedules))

    assert len(json.loads((tmp_path / "all.json").read_text(encoding="utf-8"))) == 2
    one = (tmp_path / "one.csv").read_text(encoding="utf-8")
    assert one == "\n".join(i.as_csv() for i in real_schedules[1])
    assert f"Wrote 2 schedule(s) to {(tmp_path / 'all.json').resolve()}" in console.output
    assert f"Wrote 1 schedule(s) to {(tmp_path / 'one.csv').resolve()}" in console.output


def test_clear_results(real_schedules):
    session = session_with(real_schedules)
    console = ScriptedConsole(["4"])

    manage_results(console, session)

    assert CLEARED in console.output
    assert session.results.is_empty()


def test_main_menu_wires_run_and_results_commands():
    commands = dict(MENU)

    assert commands["Run Schedule"] is run_schedule
    assert commands["Generated schedules"] is manage_results


def test_main_menu_invalid_choice_then_results_without_a_run():
    labels = [label for label, _ in MENU]
    results_option = str(labels.index("Generated schedules") + 1)
    quit_option = str(len(MENU) + 1)
    console = ScriptedConsole(["0", results_option, quit_option])

    run(console, Session())

    assert INVALID_CHOICE in console.output
    assert NO_RESULTS in console.output
    assert console.output[-1] == GOODBYE
    assert console.output.count(f"  1) {labels[0]}") == 3
