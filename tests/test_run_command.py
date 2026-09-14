import json
from functools import partial

import pytest
from scheduler import OptimizerFlags

from tests.helpers import FakeSchedulerFactory, ScriptedConsole
from zimpasta.command import CommandError, Registry, evaluate
from zimpasta.commands.run import (
    BAD_LIMIT,
    CANCELLED,
    CONFIG_PROMPT,
    FORMAT_PROMPT,
    LIMIT_PROMPT,
    NO_CONFIG,
    NO_CONFIG_PROMPT,
    OPTIMIZE_PROMPT,
    make_specs,
)
from zimpasta.generate import REASON_EXHAUSTED, REASON_TIMEOUT, generate_schedules
from zimpasta.prompts import (
    INVALID_YES_NO,
    NON_NUMERIC,
    OUTPUT_FILE_PROMPT,
    UNSUPPORTED_FORMAT,
    UNWRITABLE_FILENAME,
    VALID_FILENAME_PROMPT,
)
from zimpasta.session import Session


def run(console, session, line, generator):
    evaluate(console, session, line, Registry(make_specs(generator=generator)))


def running_line(console):
    return next(line for line in console.output if line.startswith("Running: "))


def test_bare_run_prompts_for_everything_then_exports(
    tmp_path, config_file, fake_generator, fake_factory
):
    out = tmp_path / "schedules"
    console = ScriptedConsole([str(config_file), "2", "yes", "csv", str(out)])
    session = Session()

    run(console, session, "run", fake_generator)

    written = tmp_path / "schedules.csv"
    assert written.exists()
    assert f"Wrote 2 schedule(s) to {written.resolve()}" in console.output
    assert "Generated 2 schedule(s)." in console.output
    assert "  schedule 1 of 2 found" in console.output
    assert running_line(console) == (
        f"Running: run schedule --config {config_file} --limit 2 --optimize yes "
        f"--format csv --output {written.resolve()}"
    )
    assert session.config is not None
    assert session.config_path == config_file.resolve()
    assert len(session.results) == 2
    assert fake_factory.last_config.limit == 2
    assert fake_factory.last_config.optimizer_flags == list(OptimizerFlags)
    assert console.prompts == [
        CONFIG_PROMPT.format(default="none"),
        LIMIT_PROMPT.format(default=session.config.limit),
        OPTIMIZE_PROMPT,
        FORMAT_PROMPT,
        OUTPUT_FILE_PROMPT,
    ]


def test_full_command_runs_without_prompting(tmp_path, config_file):
    out = tmp_path / "real.json"
    console = ScriptedConsole()
    session = Session()
    line = (
        f'run schedule --config "{config_file}" --limit 1 --optimize no '
        f'--format JSON --output "{out}"'
    )

    run(console, session, line, partial(generate_schedules, solver_timeout_ms=10_000))

    assert console.prompts == []
    assert not any(line.startswith("Running: ") for line in console.output)
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 1
    assert f"Wrote 1 schedule(s) to {out.resolve()}" in console.output
    assert session.config_path == config_file.resolve()


def test_partial_command_prompts_only_for_what_is_missing(tmp_path, config, fake_generator):
    session = Session(config=config)
    console = ScriptedConsole(["no", str(tmp_path / "out")])

    run(console, session, "run --limit 1 --format csv", fake_generator)

    assert console.prompts == [OPTIMIZE_PROMPT, OUTPUT_FILE_PROMPT]
    assert (tmp_path / "out.csv").exists()
    assert "--config" not in running_line(console)


def test_partial_command_asks_for_config_when_none_is_loaded(tmp_path, config_file, fake_generator):
    console = ScriptedConsole([str(config_file), "no", str(tmp_path / "out")])

    run(console, Session(), "run --limit 1 --format csv", fake_generator)

    assert console.prompts[0] == CONFIG_PROMPT.format(default="none")
    assert f"--config {config_file}" in running_line(console)
    assert (tmp_path / "out.csv").exists()


def test_blank_config_reuses_loaded_configuration(tmp_path, config, fake_generator):
    session = Session(config=config)
    console = ScriptedConsole(["", "", "no", "csv", str(tmp_path / "out")])

    run(console, session, "run", fake_generator)

    assert console.prompts[0] == CONFIG_PROMPT.format(default="current configuration")
    assert session.config is config
    assert "--config" not in running_line(console)
    assert (tmp_path / "out.csv").exists()


def test_non_numeric_limit_reprompts(tmp_path, config, fake_generator, fake_factory):
    console = ScriptedConsole(["", "five", "1", "no", "csv", str(tmp_path / "out")])

    run(console, Session(config=config), "run", fake_generator)

    assert NON_NUMERIC in console.output
    assert console.prompts.count(LIMIT_PROMPT.format(default=config.limit)) == 2
    assert fake_factory.last_config.limit == 1


def test_unsupported_format_reprompts(tmp_path, config, fake_generator):
    console = ScriptedConsole(["", "", "no", "xml", "Json", str(tmp_path / "out")])

    run(console, Session(config=config), "run", fake_generator)

    assert UNSUPPORTED_FORMAT in console.output
    assert console.prompts.count(FORMAT_PROMPT) == 2
    assert (tmp_path / "out.json").exists()


def test_unwritable_filename_reprompts(tmp_path, config, fake_generator):
    bad = tmp_path / "no_such_dir" / "out"
    console = ScriptedConsole(["", "", "no", "csv", str(bad), str(tmp_path / "out")])

    run(console, Session(config=config), "run", fake_generator)

    assert UNWRITABLE_FILENAME in console.output
    assert console.prompts[-1] == f"{VALID_FILENAME_PROMPT} "
    assert (tmp_path / "out.csv").exists()


def test_invalid_optimization_choice_reprompts(tmp_path, config, fake_generator, fake_factory):
    console = ScriptedConsole(["", "", "sure", "yes", "csv", str(tmp_path / "out")])

    run(console, Session(config=config), "run", fake_generator)

    assert INVALID_YES_NO in console.output
    assert console.prompts.count(OPTIMIZE_PROMPT) == 2
    assert fake_factory.last_config.optimizer_flags == list(OptimizerFlags)


def test_existing_output_file_asks_before_overwriting(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole(["", "", "no", "csv", str(existing), "yes"])

    run(console, Session(config=config), "run", fake_generator)

    assert existing.read_text(encoding="utf-8") != "old"
    assert any("already exists. Overwrite? (yes/no): " in p for p in console.prompts)
    assert running_line(console).endswith("--overwrite")


def test_declining_overwrite_returns_to_filename_prompt(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole(["", "", "no", "csv", str(existing), "no", str(tmp_path / "other")])

    run(console, Session(config=config), "run", fake_generator)

    assert existing.read_text(encoding="utf-8") == "old"
    assert (tmp_path / "other.csv").exists()


def test_full_command_without_overwrite_flag_still_confirms(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole(["yes"])
    line = f'run schedule --limit 2 --optimize no --format csv --output "{existing}"'

    run(console, Session(config=config), line, fake_generator)

    assert existing.read_text(encoding="utf-8") != "old"
    assert len(console.prompts) == 1 and "Overwrite? (yes/no): " in console.prompts[0]


def test_overwrite_flag_replaces_without_asking(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole()
    line = f'run schedule --limit 2 --optimize no --format csv --output "{existing}" --overwrite'

    run(console, Session(config=config), line, fake_generator)

    assert existing.read_text(encoding="utf-8") != "old"
    assert console.prompts == []


def test_file_created_during_generation_is_not_silently_overwritten(
    tmp_path, config, real_schedules
):
    out = tmp_path / "out.csv"

    class SneakyFactory(FakeSchedulerFactory):
        def __call__(self, config, *, solver_timeout_ms=None):
            out.write_text("appeared mid-solve", encoding="utf-8")
            return super().__call__(config, solver_timeout_ms=solver_timeout_ms)

    generator = partial(generate_schedules, scheduler_factory=SneakyFactory(real_schedules))
    console = ScriptedConsole(["", "", "no", "csv", str(out), "no", str(tmp_path / "safe")])

    run(console, Session(config=config), "run", generator)

    assert out.read_text(encoding="utf-8") == "appeared mid-solve"
    assert (tmp_path / "safe.csv").exists()


def test_no_feasible_schedule_writes_nothing(tmp_path, config, real_schedules):
    out = tmp_path / "out.csv"
    cases = ((REASON_EXHAUSTED, "No feasible schedule"), (REASON_TIMEOUT, "timed out"))
    for reason, phrase in cases:
        factory = FakeSchedulerFactory([], reason=reason)
        console = ScriptedConsole(["", "", "no", "csv", str(out)])
        session = Session(config=config)

        run(console, session, "run", partial(generate_schedules, scheduler_factory=factory))

        assert any(phrase in line for line in console.output)
        assert f"Nothing was written to {out.resolve()}." in console.output
        assert not out.exists()
        assert session.results.is_empty()


def test_runtime_failure_keeps_previous_results_and_config(tmp_path, config, real_schedules):
    good = partial(generate_schedules, scheduler_factory=FakeSchedulerFactory(real_schedules))
    session = Session(config=config)
    run(ScriptedConsole(["", "", "no", "csv", str(tmp_path / "first")]), session, "run", good)
    previous = session.results.result

    broken = FakeSchedulerFactory([], error=RuntimeError("solver crashed"))
    console = ScriptedConsole(["", "", "no", "csv", str(tmp_path / "second")])
    run(console, session, "run", partial(generate_schedules, scheduler_factory=broken))

    assert any("Unexpected error while generating schedules" in line for line in console.output)
    assert any("solver crashed" in line for line in console.output)
    assert session.results.result is previous
    assert session.config is config
    assert not (tmp_path / "second.csv").exists()


def test_invalid_config_file_reprompts_and_keeps_previous_config(
    tmp_path, config, config_file, fake_generator
):
    missing = tmp_path / "missing.json"
    not_json = tmp_path / "bad.json"
    not_json.write_text("{", encoding="utf-8")
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"config": {}}), encoding="utf-8")
    answers = [str(missing), str(not_json), str(invalid), str(config_file)]
    answers += ["", "no", "csv", str(tmp_path / "out")]
    console = ScriptedConsole(answers)
    session = Session(config=config)

    run(console, session, "run", fake_generator)

    assert any("Cannot read config file" in line for line in console.output)
    assert any("is not valid JSON" in line for line in console.output)
    assert any("is not a valid configuration" in line for line in console.output)
    assert console.prompts.count(CONFIG_PROMPT.format(default="current configuration")) == 4
    assert session.config_path == config_file.resolve()
    assert (tmp_path / "out.csv").exists()


def test_blank_config_without_loaded_config_reprompts(tmp_path, config_file, fake_generator):
    console = ScriptedConsole(["", str(config_file), "", "no", "csv", str(tmp_path / "out")])

    run(console, Session(), "run", fake_generator)

    assert NO_CONFIG_PROMPT in console.output
    assert (tmp_path / "out.csv").exists()


def test_full_command_errors_are_command_errors(tmp_path, config, fake_generator):
    out = str(tmp_path / "out")

    with pytest.raises(CommandError, match=NO_CONFIG):
        run(
            ScriptedConsole(),
            Session(),
            f"run schedule --limit 2 --optimize no --format csv --output {out}",
            fake_generator,
        )

    with pytest.raises(CommandError, match="Cannot read config file"):
        run(
            ScriptedConsole(),
            Session(),
            f"run schedule --config {tmp_path / 'nope.json'} --limit 2 --optimize no "
            f"--format csv --output {out}",
            fake_generator,
        )

    with pytest.raises(CommandError, match=BAD_LIMIT):
        run(
            ScriptedConsole(),
            Session(config=config),
            f"run schedule --limit 0 --optimize no --format csv --output {out}",
            fake_generator,
        )

    with pytest.raises(CommandError, match="--format must be one of"):
        run(
            ScriptedConsole(),
            Session(config=config),
            f"run schedule --limit 2 --optimize no --format xml --output {out}",
            fake_generator,
        )

    assert not (tmp_path / "out.csv").exists()


def test_bad_config_option_in_partial_command_is_reported(tmp_path, fake_generator):
    console = ScriptedConsole()

    with pytest.raises(CommandError, match="Cannot read config file"):
        run(console, Session(), f"run --config {tmp_path / 'nope.json'}", fake_generator)

    assert console.prompts == []


def test_end_of_input_cancels_without_raising(config, fake_generator):
    class EOFConsole(ScriptedConsole):
        def ask(self, prompt):
            raise EOFError

    console = EOFConsole()

    run(console, Session(config=config), "run", fake_generator)

    assert console.output[-1] == CANCELLED
