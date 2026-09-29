"""Schedule generation as a background job the GUI can watch, and cancel.

A run can take minutes (each schedule is a full solve), so :class:`GenerationJob` runs
:func:`~zimpasta.model.generate.generate_schedules` on a worker thread and exposes its
progress as a :class:`JobStatus`. Only one run at a time: starting while another runs
raises :class:`GenerationBusy`, which guards against a double-clicked Generate button.

Overrides
---------
The generation limit and optimizer flags can be overridden for one run. They are
checked by the library before the run starts: :func:`plan_run` applies them to a copy
of the configuration and validates it, raising :class:`InvalidOverrides` with located
issues if the library rejects them. The configuration itself is never modified, so the
configured values stay available and saved files never change.

Outcomes
--------
``succeeded``     one or more schedules; ``on_success`` receives them.
``infeasible``    the configuration is valid but no schedule satisfies every constraint.
``solver_error``  the solver timed out, could not decide, or raised its own error.
``failed``        anything unexpected. The message is friendly; ``detail`` has specifics.
``cancelled``     stopped on request after the schedule in progress finished.

Only ``succeeded`` changes results. Every other outcome leaves earlier results as they were.
"""

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.model.generate import (
    DEFAULT_SOLVER_TIMEOUT_MS,
    REASON_EXHAUSTED,
    REASON_TIMEOUT,
    GenerationCancelled,
    GenerationFailed,
    GenerationOutcome,
    GenerationResult,
    GenerationSuccess,
    InvalidConfiguration,
    NoFeasibleSchedule,
    describe_reason,
    generate_schedules,
)
from zimpasta.model.issues import Issue, issues_from_error


class JobState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    INFEASIBLE = "infeasible"
    SOLVER_ERROR = "solver_error"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationBusy(Exception):
    code = "generation_running"

    def __init__(self) -> None:
        self.message = "Schedules are already being generated. Wait for that run or cancel it."
        super().__init__(self.message)


class InvalidOverrides(Exception):
    code = "invalid_overrides"

    def __init__(self, issues: tuple[Issue, ...]) -> None:
        self.issues = issues
        details = " ".join(f"{problem.field or 'value'}: {problem.message}" for problem in issues)
        self.message = f"The run settings are not valid, so nothing was started. {details}"
        super().__init__(self.message)


@dataclass(frozen=True)
class RunSettings:
    """The limit and optimizer flags a run uses, next to the configured values."""

    limit: int
    optimizer_flags: tuple[str, ...]
    configured_limit: int
    configured_optimizer_flags: tuple[str, ...]

    @property
    def limit_overridden(self) -> bool:
        return self.limit != self.configured_limit

    @property
    def optimizer_flags_overridden(self) -> bool:
        return set(self.optimizer_flags) != set(self.configured_optimizer_flags)

    def to_dict(self) -> dict:
        return {
            "limit": self.limit,
            "optimizer_flags": list(self.optimizer_flags),
            "configured_limit": self.configured_limit,
            "configured_optimizer_flags": list(self.configured_optimizer_flags),
            "limit_overridden": self.limit_overridden,
            "optimizer_flags_overridden": self.optimizer_flags_overridden,
        }


@dataclass(frozen=True)
class JobStatus:
    state: JobState = JobState.IDLE
    found: int = 0
    settings: RunSettings | None = None
    config_name: str | None = None
    config_revision: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None
    detail: str | None = None
    completion_reason: str | None = None
    cancel_requested: bool = False

    @property
    def running(self) -> bool:
        return self.state is JobState.RUNNING

    def to_dict(self, now: datetime | None = None) -> dict:
        end = self.finished_at or now
        elapsed = (end - self.started_at).total_seconds() if self.started_at and end else None
        return {
            "state": self.state.value,
            "running": self.running,
            "found": self.found,
            "settings": self.settings.to_dict() if self.settings else None,
            "config_name": self.config_name,
            "config_revision": self.config_revision,
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
            "elapsed_seconds": round(elapsed, 1) if elapsed is not None else None,
            "message": self.message,
            "detail": self.detail,
            "completion_reason": self.completion_reason,
            "cancel_requested": self.cancel_requested,
        }


def plan_run(
    config: CombinedConfig,
    *,
    limit: object = None,
    optimizer_flags: object = None,
) -> RunSettings:
    """Check one run's overrides with the library and return the settings it will use.

    ``None`` means "use the configured value".

    Raises:
        InvalidOverrides: the library rejects the overridden limit or flags.
    """
    data = json.loads(config.model_dump_json())
    if limit is not None:
        data["limit"] = limit
    if optimizer_flags is not None:
        data["optimizer_flags"] = optimizer_flags
    try:
        run = CombinedConfig.model_validate(data)
    except ValidationError as error:
        raise InvalidOverrides(tuple(issues_from_error(error))) from None
    return RunSettings(
        limit=run.limit,
        optimizer_flags=tuple(flag.value for flag in run.optimizer_flags),
        configured_limit=config.limit,
        configured_optimizer_flags=tuple(flag.value for flag in config.optimizer_flags),
    )


SuccessHandler = Callable[[GenerationResult, JobStatus], None]


class GenerationJob:
    """At most one schedule-generation run at a time, on a worker thread."""

    def __init__(
        self,
        *,
        generator: Callable[..., GenerationOutcome] = generate_schedules,
        on_success: SuccessHandler | None = None,
        clock: Callable[[], datetime] = datetime.now,
        solver_timeout_ms: int | None = DEFAULT_SOLVER_TIMEOUT_MS,
    ) -> None:
        self._generator = generator
        self._on_success = on_success
        self._clock = clock
        self._solver_timeout_ms = solver_timeout_ms
        self._lock = threading.Lock()
        self._status = JobStatus()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    def status(self) -> JobStatus:
        with self._lock:
            return self._status

    def start(
        self,
        config: CombinedConfig,
        *,
        limit: object = None,
        optimizer_flags: object = None,
        config_name: str | None = None,
        config_revision: int | None = None,
    ) -> JobStatus:
        """Validate the overrides and start a run in the background.

        Raises:
            GenerationBusy: a run is already in progress.
            InvalidOverrides: the library rejects the overrides. Nothing is started.
        """
        with self._lock:
            if self._status.running:
                raise GenerationBusy()
        settings = plan_run(config, limit=limit, optimizer_flags=optimizer_flags)
        with self._lock:
            if self._status.running:
                raise GenerationBusy()
            self._cancel = threading.Event()
            self._status = JobStatus(
                state=JobState.RUNNING,
                settings=settings,
                config_name=config_name,
                config_revision=config_revision,
                started_at=self._clock(),
                message=f"Generating up to {settings.limit} schedules...",
            )
            status = self._status
            self._thread = threading.Thread(
                target=self._run,
                args=(config, settings, self._cancel),
                name="zimpasta-generation",
                daemon=True,
            )
            self._thread.start()
            return status

    def cancel(self) -> JobStatus:
        """Ask a running job to stop after the schedule it is working on."""
        with self._lock:
            if self._status.running:
                self._cancel.set()
                self._status = replace(
                    self._status,
                    cancel_requested=True,
                    message="Cancelling after the current schedule...",
                )
            return self._status

    def wait(self, timeout: float | None = None) -> JobStatus:
        """Block until the current run finishes (for tests and the shell)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.status()

    def _progress(self, found: int, limit: int) -> None:
        with self._lock:
            if self._status.running:
                message = self._status.message
                if not self._status.cancel_requested:
                    message = f"Generating... {found} of {limit} schedules found."
                self._status = replace(self._status, found=found, message=message)

    def _run(self, config: CombinedConfig, settings: RunSettings, cancel: threading.Event) -> None:
        try:
            outcome = self._generator(
                config,
                limit=settings.limit,
                optimizer_flags=list(settings.optimizer_flags),
                solver_timeout_ms=self._solver_timeout_ms,
                on_progress=self._progress,
                should_stop=cancel.is_set,
            )
        except Exception as error:  # the generator already classifies solver errors
            outcome = GenerationFailed(f"{type(error).__name__}: {error}", error)
        self._finish(outcome)

    def _finish(self, outcome: GenerationOutcome) -> None:
        with self._lock:
            status = replace(self._status, finished_at=self._clock())
        match outcome:
            case GenerationSuccess(result=result):
                count = result.count
                message = f"{count} {'schedule' if count == 1 else 'schedules'} generated."
                if not result.reached_limit:
                    message += f" Stopped early: {describe_reason(result.completion_reason)}."
                status = replace(
                    status,
                    state=JobState.SUCCEEDED,
                    found=count,
                    message=message,
                    completion_reason=result.completion_reason,
                )
                if self._on_success is not None:
                    try:
                        self._on_success(result, status)
                    except Exception as error:
                        status = replace(
                            status,
                            state=JobState.FAILED,
                            message="Schedules were generated but could not be stored.",
                            detail=f"{type(error).__name__}: {error}",
                        )
            case NoFeasibleSchedule(reason=reason) if reason == REASON_EXHAUSTED:
                status = replace(
                    status,
                    state=JobState.INFEASIBLE,
                    completion_reason=reason,
                    message=(
                        "No feasible schedule. The configuration is valid, but its "
                        "constraints conflict."
                    ),
                )
            case NoFeasibleSchedule(reason=reason):
                message = (
                    "The solver timed out before finding a schedule."
                    if reason == REASON_TIMEOUT
                    else "The solver could not decide whether a schedule exists."
                )
                status = replace(
                    status, state=JobState.SOLVER_ERROR, completion_reason=reason, message=message
                )
            case GenerationCancelled(found=found):
                status = replace(
                    status,
                    state=JobState.CANCELLED,
                    found=found,
                    message="Generation cancelled. Earlier results are unchanged.",
                )
            case GenerationFailed(message=detail, exception=error) if _from_solver(error):
                status = replace(
                    status,
                    state=JobState.SOLVER_ERROR,
                    message="The scheduler reported an error while solving.",
                    detail=detail,
                )
            case GenerationFailed(message=detail):
                status = replace(
                    status,
                    state=JobState.FAILED,
                    message=(
                        "Something went wrong while generating schedules. The configuration "
                        "and earlier results are unchanged."
                    ),
                    detail=detail,
                )
            case InvalidConfiguration(errors=errors):
                status = replace(
                    status,
                    state=JobState.FAILED,
                    message="The configuration was rejected when the run started.",
                    detail="; ".join(errors),
                )
        with self._lock:
            self._status = status


def _from_solver(error: BaseException | None) -> bool:
    return error is not None and type(error).__module__.split(".")[0] == "z3"


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat(timespec="seconds") if moment else None
