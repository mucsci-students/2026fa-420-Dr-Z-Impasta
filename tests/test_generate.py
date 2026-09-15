from scheduler import CombinedConfig, OptimizerFlags

from tests.helpers import FakeSchedulerFactory, build_config_data, build_infeasible_config_data
from zimpasta.generate import (
    REASON_EXHAUSTED,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    GenerationFailed,
    GenerationSuccess,
    InvalidConfiguration,
    NoFeasibleSchedule,
    describe_reason,
    generate_schedules,
    prepare_run_config,
    resolve_optimizer_flags,
)


def test_real_solve_generates_up_to_the_limit(config):
    outcome = generate_schedules(config, solver_timeout_ms=10_000)

    assert isinstance(outcome, GenerationSuccess)
    assert outcome.result.count == config.limit
    assert outcome.result.reached_limit
    assert outcome.result.completion_reason is None
    for schedule in outcome.result.schedules:
        assert {instance.course_str for instance in schedule} == {"CS 101.01", "CS 102.01"}


def test_real_infeasible_config_reports_no_feasible_schedule():
    config = CombinedConfig.model_validate(build_infeasible_config_data())

    outcome = generate_schedules(config, solver_timeout_ms=10_000)

    assert outcome == NoFeasibleSchedule(REASON_EXHAUSTED)


def test_limit_override_and_progress(config, real_schedules):
    factory = FakeSchedulerFactory(real_schedules)
    progress = []

    outcome = generate_schedules(
        config, limit=1, scheduler_factory=factory, on_progress=lambda k, n: progress.append((k, n))
    )

    assert isinstance(outcome, GenerationSuccess)
    assert outcome.result.count == 1
    assert outcome.result.limit == 1
    assert factory.last_config.limit == 1
    assert progress == [(1, 1)]


def test_run_never_mutates_the_session_config(config, fake_factory):
    original_limit = config.limit

    generate_schedules(config, limit=1, optimize=True, scheduler_factory=fake_factory)

    assert config.limit == original_limit
    assert config.optimizer_flags == []


def test_optimize_yes_uses_all_flags_when_config_has_none(config, fake_factory):
    generate_schedules(config, optimize=True, scheduler_factory=fake_factory)

    assert fake_factory.last_config.optimizer_flags == list(OptimizerFlags)


def test_optimize_yes_keeps_config_flags_when_present(fake_factory):
    config = CombinedConfig.model_validate(build_config_data(optimizer_flags=["same_room"]))

    generate_schedules(config, optimize=True, scheduler_factory=fake_factory)

    assert fake_factory.last_config.optimizer_flags == [OptimizerFlags.SAME_ROOM]


def test_optimize_no_clears_flags(fake_factory):
    config = CombinedConfig.model_validate(build_config_data(optimizer_flags=["same_room"]))

    generate_schedules(config, optimize=False, scheduler_factory=fake_factory)

    assert fake_factory.last_config.optimizer_flags == []


def test_resolve_optimizer_flags_none_keeps_config_as_is():
    config = CombinedConfig.model_validate(build_config_data(optimizer_flags=["pack_labs"]))

    assert resolve_optimizer_flags(config, None) == (OptimizerFlags.PACK_LABS,)


def test_prepare_run_config_returns_a_validated_copy(config):
    run_config = prepare_run_config(config, limit=5, optimize=False)

    assert run_config is not config
    assert run_config.limit == 5
    assert run_config.config == config.config


def test_partial_result_records_completion_reason(config, real_schedules):
    factory = FakeSchedulerFactory(real_schedules[:1], reason=REASON_EXHAUSTED)

    outcome = generate_schedules(config, limit=3, scheduler_factory=factory)

    assert isinstance(outcome, GenerationSuccess)
    assert outcome.result.count == 1
    assert not outcome.result.reached_limit
    assert outcome.result.completion_reason == REASON_EXHAUSTED


def test_no_models_reports_the_solver_reason(config):
    for reason in (REASON_EXHAUSTED, REASON_TIMEOUT, REASON_UNKNOWN):
        factory = FakeSchedulerFactory([], reason=reason)
        assert generate_schedules(config, scheduler_factory=factory) == NoFeasibleSchedule(reason)


def test_no_models_without_a_reason_is_unknown(config):
    factory = FakeSchedulerFactory([], reason=None)

    assert generate_schedules(config, scheduler_factory=factory) == NoFeasibleSchedule(
        REASON_UNKNOWN
    )


def test_missing_config_is_invalid():
    outcome = generate_schedules(None)

    assert isinstance(outcome, InvalidConfiguration)
    assert outcome.errors == ("No configuration is loaded.",)


def test_zero_limit_fails_complete_validation(config, fake_factory):
    outcome = generate_schedules(config, limit=0, scheduler_factory=fake_factory)

    assert isinstance(outcome, InvalidConfiguration)
    assert any(line.startswith("limit:") for line in outcome.errors)
    assert fake_factory.instances == []


def test_solver_error_is_a_runtime_failure(config):
    factory = FakeSchedulerFactory([], error=RuntimeError("z3 exploded"))

    outcome = generate_schedules(config, scheduler_factory=factory)

    assert isinstance(outcome, GenerationFailed)
    assert "z3 exploded" in outcome.message
    assert isinstance(outcome.exception, RuntimeError)


def test_constructor_error_is_a_runtime_failure(config):
    def broken_factory(config, *, solver_timeout_ms=None):
        raise ValueError("bad solver options")

    outcome = generate_schedules(config, scheduler_factory=broken_factory)

    assert isinstance(outcome, GenerationFailed)
    assert "bad solver options" in outcome.message


def test_timeout_is_passed_to_the_scheduler(config, fake_factory):
    generate_schedules(config, solver_timeout_ms=1234, scheduler_factory=fake_factory)

    assert fake_factory.instances[-1].solver_timeout_ms == 1234


def test_describe_reason_wording():
    assert describe_reason(None) == "the limit was reached"
    assert describe_reason(REASON_EXHAUSTED) == "the solution space is exhausted"
    assert describe_reason("something_else") == "something_else"
