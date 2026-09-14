import json
from functools import partial

from scheduler import OptimizerFlags

from tests.helpers import FakeSchedulerFactory, ScriptedConsole
from zimpasta.commands.run import (
    CANCELLED,
    CONFIG_PROMPT,
    FORMAT_PROMPT,
    LIMIT_PROMPT,
    OPTIMIZE_PROMPT,
    run_schedule,
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


def test_run_with_valid_input_generates_and_exports(
    tmp_path, config_file, fake_generator, fake_factory
):
    out = tmp_path / "schedules"
    console = ScriptedConsole([str(config_file), "2", "yes", "csv", str(out)])
    session = Session()

    run_schedule(console, session, generator=fake_generator)

    written = tmp_path / "schedules.csv"
    assert written.exists()
    assert f"Wrote 2 schedule(s) to {written.resolve()}" in console.output
    assert "Generated 2 schedule(s)." in console.output
    assert "  schedule 1 of 2 found" in console.output
    assert session.config is not None
    assert session.config_path == config_file.resolve()
    assert len(session.results) == 2
    assert session.results.result.config_path == config_file.resolve()
    assert fake_factory.last_config.limit == 2
    assert fake_factory.last_config.optimizer_flags == list(OptimizerFlags)
    assert console.prompts == [
        CONFIG_PROMPT.format(default="none"),
        LIMIT_PROMPT.format(default=session.config.limit),
        OPTIMIZE_PROMPT,
        FORMAT_PROMPT,
        OUTPUT_FILE_PROMPT,
    ]


def test_run_with_real_solver_writes_json(tmp_path, config_file):
    out = tmp_path / "real.json"
    console = ScriptedConsole([str(config_file), "1", "no", "JSON", str(out)])

    run_schedule(
        console, Session(), generator=partial(generate_schedules, solver_timeout_ms=10_000)
    )

    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert f"Wrote 1 schedule(s) to {out.resolve()}" in console.output


def test_blank_config_reuses_loaded_configuration(tmp_path, config, fake_generator):
    session = Session(config=config)
    console = ScriptedConsole(["", "", "no", "csv", str(tmp_path / "out")])

    run_schedule(console, session, generator=fake_generator)

    assert console.prompts[0] == CONFIG_PROMPT.format(default="current configuration")
    assert session.config is config
    assert (tmp_path / "out.csv").exists()


def test_non_numeric_limit_reprompts(tmp_path, config, fake_generator, fake_factory):
    console = ScriptedConsole(["", "five", "1", "no", "csv", str(tmp_path / "out")])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert NON_NUMERIC in console.output
    assert console.prompts.count(LIMIT_PROMPT.format(default=config.limit)) == 2
    assert fake_factory.last_config.limit == 1


def test_unsupported_format_reprompts(tmp_path, config, fake_generator):
    console = ScriptedConsole(["", "", "no", "xml", "Json", str(tmp_path / "out")])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert UNSUPPORTED_FORMAT in console.output
    assert console.prompts.count(FORMAT_PROMPT) == 2
    assert (tmp_path / "out.json").exists()


def test_unwritable_filename_reprompts(tmp_path, config, fake_generator):
    bad = tmp_path / "no_such_dir" / "out"
    console = ScriptedConsole(["", "", "no", "csv", str(bad), str(tmp_path / "out")])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert UNWRITABLE_FILENAME in console.output
    assert console.prompts[-1] == f"{VALID_FILENAME_PROMPT} "
    assert (tmp_path / "out.csv").exists()


def test_invalid_optimization_choice_reprompts(tmp_path, config, fake_generator, fake_factory):
    console = ScriptedConsole(["", "", "sure", "yes", "csv", str(tmp_path / "out")])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert INVALID_YES_NO in console.output
    assert console.prompts.count(OPTIMIZE_PROMPT) == 2
    assert fake_factory.last_config.optimizer_flags == list(OptimizerFlags)


def test_existing_output_file_asks_before_overwriting(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole(["", "", "no", "csv", str(existing), "yes"])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert existing.read_text(encoding="utf-8") != "old"
    assert any("already exists. Overwrite? (yes/no): " in p for p in console.prompts)


def test_declining_overwrite_returns_to_filename_prompt(tmp_path, config, fake_generator):
    existing = tmp_path / "out.csv"
    existing.write_text("old", encoding="utf-8")
    console = ScriptedConsole(["", "", "no", "csv", str(existing), "no", str(tmp_path / "other")])

    run_schedule(console, Session(config=config), generator=fake_generator)

    assert existing.read_text(encoding="utf-8") == "old"
    assert (tmp_path / "other.csv").exists()


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

    run_schedule(console, Session(config=config), generator=generator)

    assert out.read_text(encoding="utf-8") == "appeared mid-solve"
    assert (tmp_path / "safe.csv").exists()


def test_no_feasible_schedule_writes_nothing(tmp_path, config, real_schedules):
    out = tmp_path / "out.csv"
    for reason, phrase in (
        (REASON_EXHAUSTED, "No feasible schedule"),
        (REASON_TIMEOUT, "timed out"),
    ):
        factory = FakeSchedulerFactory([], reason=reason)
        console = ScriptedConsole(["", "", "no", "csv", str(out)])
        session = Session(config=config)

        run_schedule(
            console, session, generator=partial(generate_schedules, scheduler_factory=factory)
        )

        assert any(phrase in line for line in console.output)
        assert f"Nothing was written to {out.resolve()}." in console.output
        assert not out.exists()
        assert session.results.is_empty()


def test_runtime_failure_keeps_previous_results_and_config(tmp_path, config, real_schedules):
    good = FakeSchedulerFactory(real_schedules)
    session = Session(config=config)
    run_schedule(
        ScriptedConsole(["", "", "no", "csv", str(tmp_path / "first")]),
        session,
        generator=partial(generate_schedules, scheduler_factory=good),
    )
    previous = session.results.result

    broken = FakeSchedulerFactory([], error=RuntimeError("solver crashed"))
    console = ScriptedConsole(["", "", "no", "csv", str(tmp_path / "second")])
    run_schedule(console, session, generator=partial(generate_schedules, scheduler_factory=broken))

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
    console = ScriptedConsole(
        [
            str(missing),
            str(not_json),
            str(invalid),
            str(config_file),
            "",
            "no",
            "csv",
            str(tmp_path / "out"),
        ]
    )
    session = Session(config=config)

    run_schedule(console, session, generator=fake_generator)

    assert any("Cannot read config file" in line for line in console.output)
    assert any("is not valid JSON" in line for line in console.output)
    assert any("is not a valid configuration" in line for line in console.output)
    assert console.prompts.count(CONFIG_PROMPT.format(default="current configuration")) == 4
    assert session.config_path == config_file.resolve()
    assert (tmp_path / "out.csv").exists()


def test_blank_config_without_loaded_config_reprompts(tmp_path, config_file, fake_generator):
    console = ScriptedConsole(["", str(config_file), "", "no", "csv", str(tmp_path / "out")])

    run_schedule(console, Session(), generator=fake_generator)

    assert "No configuration is loaded. Enter the path to a config file." in console.output
    assert (tmp_path / "out.csv").exists()


def test_end_of_input_cancels_without_raising(config):
    class EOFConsole(ScriptedConsole):
        def ask(self, prompt):
            raise EOFError

    console = EOFConsole()

    run_schedule(console, Session(config=config))

    assert console.output[-1] == CANCELLED
