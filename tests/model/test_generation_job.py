"""Background schedule generation: overrides, outcomes, progress, busy guard, cancel."""

import threading
from functools import partial

import anyio
import pytest
from scheduler import CombinedConfig

from tests.helpers import FakeSchedulerFactory
from zimpasta.model.generate import REASON_EXHAUSTED, REASON_TIMEOUT, generation_steps
from zimpasta.model.generation_job import (
    EventLoopRunner,
    GenerationBusy,
    GenerationJob,
    InvalidOverrides,
    JobState,
    plan_run,
)

TIMEOUT = 10


class Recorder:
    """Collects what the job hands to ``on_success``."""

    def __init__(self):
        self.calls = []

    def __call__(self, result, status):
        self.calls.append((result, status))


class GatedFactory(FakeSchedulerFactory):
    """A fake scheduler that yields one schedule each time the test calls ``step()``."""

    def __init__(self, schedules):
        super().__init__(schedules, reason=REASON_EXHAUSTED)
        self.gate = threading.Semaphore(0)
        self.waiting = threading.Event()

    def __call__(self, config, *, solver_timeout_ms=None):
        inner = super().__call__(config, solver_timeout_ms=solver_timeout_ms)
        factory = self

        class Gated:
            _enumeration_completion_reason = None

            def get_models(self):
                for schedule in inner.get_models():
                    factory.waiting.set()
                    assert factory.gate.acquire(timeout=TIMEOUT)
                    yield schedule
                self._enumeration_completion_reason = inner._enumeration_completion_reason

        return Gated()

    def step(self):
        assert self.waiting.wait(TIMEOUT)
        self.waiting.clear()
        self.gate.release()


def job_with(factory, recorder=None):
    return GenerationJob(
        generator=partial(generation_steps, scheduler_factory=factory),
        on_success=recorder,
    )


def configured(config_data, **changes) -> CombinedConfig:
    return CombinedConfig.model_validate({**config_data, **changes})


# ------------------------------------------------------------------ overrides


def test_plan_without_overrides_uses_configured_values(config_data):
    config = configured(config_data, optimizer_flags=["same_room"])

    settings = plan_run(config)

    assert (settings.limit, settings.optimizer_flags) == (3, ("same_room",))
    assert not settings.limit_overridden
    assert not settings.optimizer_flags_overridden


def test_plan_applies_overrides_without_touching_the_configuration(config_data):
    config = configured(config_data, optimizer_flags=["same_room"])

    settings = plan_run(config, limit=5, optimizer_flags=["faculty_course", "pack_rooms"])

    assert settings.to_dict()["limit"] == 5
    assert settings.optimizer_flags == ("faculty_course", "pack_rooms")
    assert settings.limit_overridden and settings.optimizer_flags_overridden
    assert config.limit == 3
    assert [flag.value for flag in config.optimizer_flags] == ["same_room"]


@pytest.mark.parametrize("limit", [0, -1, "5", True, 2.5])
def test_invalid_limit_override_is_rejected_by_the_library(config, limit):
    with pytest.raises(InvalidOverrides) as caught:
        plan_run(config, limit=limit)

    assert caught.value.issues[0].field == "limit"
    assert caught.value.message.startswith("The run settings are not valid")


@pytest.mark.parametrize("flags", [["go_fast"], "same_room", [3]])
def test_invalid_optimizer_override_is_rejected(config, flags):
    with pytest.raises(InvalidOverrides) as caught:
        plan_run(config, optimizer_flags=flags)

    assert caught.value.issues[0].field == "optimizer_flags"


# ------------------------------------------------------------------ outcomes


def test_success_passes_overrides_and_hands_results_over(config, real_schedules):
    factory = FakeSchedulerFactory(real_schedules)
    recorder = Recorder()
    job = job_with(factory, recorder)

    started = job.start(
        config,
        limit=2,
        optimizer_flags=["pack_labs"],
        config_name="minimal.json",
        config_revision=4,
    )
    assert started.running
    status = job.wait(TIMEOUT)

    assert status.state is JobState.SUCCEEDED
    assert status.found == 2
    assert status.message == "2 schedules generated."
    assert factory.last_config.limit == 2
    assert [flag.value for flag in factory.last_config.optimizer_flags] == ["pack_labs"]
    [(result, handed)] = recorder.calls
    assert result.count == 2
    assert handed.config_name == "minimal.json" and handed.config_revision == 4
    assert config.limit == 3 and config.optimizer_flags == []
    as_dict = status.to_dict()
    assert as_dict["state"] == "succeeded"
    assert as_dict["elapsed_seconds"] is not None
    assert as_dict["settings"]["limit_overridden"] is True


def test_fewer_than_requested_says_why(config, real_schedules):
    job = job_with(FakeSchedulerFactory(real_schedules[:1], reason=REASON_EXHAUSTED))

    job.start(config)
    status = job.wait(TIMEOUT)

    assert status.state is JobState.SUCCEEDED
    assert "Stopped early: the solution space is exhausted." in status.message


def test_no_feasible_schedule(config):
    recorder = Recorder()
    job = job_with(FakeSchedulerFactory([], reason=REASON_EXHAUSTED), recorder)

    job.start(config)
    status = job.wait(TIMEOUT)

    assert status.state is JobState.INFEASIBLE
    assert "constraints conflict" in status.message
    assert recorder.calls == []


def test_solver_timeout_is_a_solver_error(config):
    job = job_with(FakeSchedulerFactory([], reason=REASON_TIMEOUT))

    job.start(config)
    status = job.wait(TIMEOUT)

    assert status.state is JobState.SOLVER_ERROR
    assert status.message == "The solver timed out before finding a schedule."


def test_solver_exception_is_a_solver_error_and_others_are_failures(config):
    solver_error = type("Z3Exception", (Exception,), {"__module__": "z3.z3types"})

    job = job_with(FakeSchedulerFactory([], error=solver_error("model error")))
    job.start(config)
    assert job.wait(TIMEOUT).state is JobState.SOLVER_ERROR

    job = job_with(FakeSchedulerFactory([], error=RuntimeError("disk on fire")))
    job.start(config)
    status = job.wait(TIMEOUT)
    assert status.state is JobState.FAILED
    assert "earlier results are unchanged" in status.message
    assert "disk on fire" in status.detail


def test_a_failing_success_handler_is_reported(config, real_schedules):
    def broken(result, status):
        raise ValueError("no room at the inn")

    job = job_with(FakeSchedulerFactory(real_schedules), broken)
    job.start(config)
    status = job.wait(TIMEOUT)

    assert status.state is JobState.FAILED
    assert "could not be stored" in status.message


def test_real_solve(config):
    recorder = Recorder()
    job = GenerationJob(on_success=recorder)

    job.start(config, limit=1)
    status = job.wait(60)

    assert status.state is JobState.SUCCEEDED
    assert recorder.calls[0][0].count == 1


# ------------------------------------------------------ progress, busy, cancel


def test_progress_and_busy_guard(config, real_schedules):
    factory = GatedFactory(real_schedules)
    job = job_with(factory)
    job.start(config, limit=2)

    factory.step()
    factory.waiting.wait(TIMEOUT)
    assert job.status().found == 1
    assert job.status().message == "Generating... 1 of 2 schedules found."
    with pytest.raises(GenerationBusy):
        job.start(config)

    factory.step()
    assert job.wait(TIMEOUT).state is JobState.SUCCEEDED


def test_cancel_stops_after_the_current_schedule_and_keeps_old_results(config, real_schedules):
    factory = GatedFactory(real_schedules)
    recorder = Recorder()
    job = job_with(factory, recorder)
    job.start(config, limit=2)

    requested = job.cancel()
    assert requested.cancel_requested
    assert requested.message.startswith("Cancelling")
    factory.step()
    status = job.wait(TIMEOUT)

    assert status.state is JobState.CANCELLED
    assert status.found == 1
    assert recorder.calls == []


def test_cancel_when_idle_does_nothing():
    job = GenerationJob()

    assert job.cancel().state is JobState.IDLE
    assert job.wait().state is JobState.IDLE


# ------------------------------------------------------------------ the cap


def test_a_configured_limit_above_the_cap_is_lowered_for_the_run(config_data):
    config = configured(config_data, limit=100)

    settings = plan_run(config, max_limit=5)

    assert settings.limit == 5 and settings.limit_capped
    assert not settings.limit_overridden
    assert settings.to_dict()["max_limit"] == 5
    assert config.limit == 100


def test_an_override_above_the_cap_is_rejected(config):
    with pytest.raises(InvalidOverrides) as caught:
        plan_run(config, limit=6, max_limit=5)

    [problem] = caught.value.issues
    assert (problem.code, problem.area, problem.field) == (
        "limit_above_maximum",
        "settings",
        "limit",
    )
    assert "at most 5 schedules" in problem.message


def test_limits_within_the_cap_are_used_as_given(config):
    assert plan_run(config, max_limit=5).limit == 3
    settings = plan_run(config, limit=5, max_limit=5)
    assert settings.limit == 5 and settings.limit_overridden and not settings.limit_capped


def test_a_capped_run_says_so(config_data, real_schedules):
    job = GenerationJob(
        generator=partial(generation_steps, scheduler_factory=FakeSchedulerFactory(real_schedules)),
        max_limit=2,
    )

    started = job.start(configured(config_data, limit=10))

    assert started.message.startswith("Generating up to 2 schedules, the most a run generates")
    assert "asks for 10" in started.message
    assert job.wait(TIMEOUT).state is JobState.SUCCEEDED


# ------------------------------------------------------- the event-loop runner


@pytest.fixture
def anyio_backend():
    return "asyncio"


def loop_job(factory, recorder=None):
    runner = EventLoopRunner(pause=0.05)
    job = GenerationJob(
        generator=partial(generation_steps, scheduler_factory=factory),
        on_success=recorder,
        runner=runner,
    )
    return job, runner


@pytest.mark.anyio
async def test_the_event_loop_runner_generates_without_a_thread(config, real_schedules):
    recorder = Recorder()
    job, runner = loop_job(FakeSchedulerFactory(real_schedules), recorder)

    started = job.start(config, limit=2)
    assert started.running and job.status().found == 0  # nothing solved until the loop runs
    await runner.finished()

    assert job.status().state is JobState.SUCCEEDED
    assert recorder.calls[0][0].count == 2


@pytest.mark.anyio
async def test_the_event_loop_runner_cancels_between_schedules(config, real_schedules):
    recorder = Recorder()
    job, runner = loop_job(FakeSchedulerFactory(real_schedules), recorder)
    job.start(config, limit=2)

    while job.status().found < 1:
        await anyio.sleep(0.001)
    job.cancel()
    await runner.finished()

    status = job.status()
    assert status.state is JobState.CANCELLED and status.found == 1
    assert recorder.calls == []


def test_an_event_loop_run_cannot_be_waited_for_synchronously():
    with pytest.raises(RuntimeError, match="await finished"):
        EventLoopRunner().wait()
