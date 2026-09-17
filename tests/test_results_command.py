import json
from datetime import datetime

import pytest

from tests.helpers import ScriptedConsole
from zimpasta.cli import build_registry
from zimpasta.command import CommandError, Registry, evaluate
from zimpasta.commands.results import BAD_WHICH, CLEARED, NO_RESULTS, SPECS, WHICH_PROMPT
from zimpasta.generate import GenerationResult
from zimpasta.prompts import OUTPUT_FILE_PROMPT
from zimpasta.session import Session

REGISTRY = Registry(SPECS)


def run(console, session, line):
    evaluate(console, session, line, REGISTRY)


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


@pytest.mark.parametrize(
    "line",
    [
        "schedules summary",
        "schedules show 1",
        "schedules show",
        "schedules export",
        "schedules clear",
    ],
)
def test_every_schedules_command_reports_missing_results(line):
    console = ScriptedConsole()

    run(console, Session(), line)

    assert console.output == [NO_RESULTS]
    assert console.prompts == []


def test_summary(real_schedules):
    console = ScriptedConsole()

    run(console, session_with(real_schedules), "schedules summary")

    assert console.output[0].startswith("Generated schedules: 2 (limit 2)")


def test_show_full_and_via_builder(real_schedules):
    console = ScriptedConsole()
    run(console, session_with(real_schedules), "schedules show 2")
    assert console.output[0].startswith("Schedule 2")
    assert "CS 101.01" in console.output[0] and "(lab)" in console.output[0]

    console = ScriptedConsole(["9", "1"])
    run(console, session_with(real_schedules), "schedules show")
    assert "Please enter a number between 1 and 2." in console.output
    assert "Running: schedules show 1" in console.output
    assert any(line.startswith("Schedule 1") for line in console.output)


def test_show_out_of_range_is_a_command_error(real_schedules):
    with pytest.raises(CommandError, match="between 1 and 2"):
        run(ScriptedConsole(), session_with(real_schedules), "schedules show 3")
    with pytest.raises(CommandError, match="between 1 and 2"):
        run(ScriptedConsole(), session_with(real_schedules), "schedules show two")


def test_export_all_and_one_as_full_commands(tmp_path, real_schedules):
    session = session_with(real_schedules)
    console = ScriptedConsole()

    run(console, session, f'schedules export all --format json --output "{tmp_path / "all"}"')
    run(console, session, f'schedules export 2 --format CSV --output "{tmp_path / "one"}"')

    assert len(json.loads((tmp_path / "all.json").read_text(encoding="utf-8"))) == 2
    one = (tmp_path / "one.csv").read_text(encoding="utf-8")
    assert one == "\n".join(i.as_csv() for i in real_schedules[1])
    assert console.prompts == []
    assert f"Wrote 2 schedule(s) to {(tmp_path / 'all.json').resolve()}" in console.output
    assert f"Wrote 1 schedule(s) to {(tmp_path / 'one.csv').resolve()}" in console.output


def test_export_via_builder_prompts_for_missing_parts(tmp_path, real_schedules):
    console = ScriptedConsole(["nope", "ALL", "json", str(tmp_path / "out")])

    run(console, session_with(real_schedules), "schedules export")

    assert console.prompts[:2] == [WHICH_PROMPT.format(count=2)] * 2
    assert BAD_WHICH.format(count=2) in console.output
    assert console.prompts[-1] == OUTPUT_FILE_PROMPT
    assert (tmp_path / "out.json").exists()

    console = ScriptedConsole([str(tmp_path / "one")])
    run(console, session_with(real_schedules), "schedules export 1 --format csv")
    assert console.prompts == [OUTPUT_FILE_PROMPT]
    assert (tmp_path / "one.csv").exists()


def test_export_bad_which_is_a_command_error(tmp_path, real_schedules):
    with pytest.raises(CommandError, match="between 1 and 2"):
        run(
            ScriptedConsole(),
            session_with(real_schedules),
            f"schedules export 5 --format csv --output {tmp_path / 'x'}",
        )


def test_export_existing_file_confirms_or_uses_flag(tmp_path, real_schedules):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    session = session_with(real_schedules)

    console = ScriptedConsole(["no", str(tmp_path / "other")])
    run(console, session, f'schedules export all --format csv --output "{existing}"')
    assert existing.read_text(encoding="utf-8") == "old"
    assert (tmp_path / "other.csv").exists()

    console = ScriptedConsole()
    run(console, session, f'schedules export all --format csv --output "{existing}" --overwrite')
    assert existing.read_text(encoding="utf-8") != "old"
    assert console.prompts == []


def test_clear(real_schedules):
    session = session_with(real_schedules)
    console = ScriptedConsole()

    run(console, session, "schedules clear")

    assert CLEARED in console.output
    assert session.results.is_empty()


def test_shell_registry_has_the_run_and_schedules_commands_implemented():
    implemented = {spec.name: spec.implemented for spec in build_registry()}

    assert implemented["run schedule"] is True
    for noun in ("summary", "show", "export", "clear"):
        assert implemented[f"schedules {noun}"] is True
    assert implemented["display"] is True
