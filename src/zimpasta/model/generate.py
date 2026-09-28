"""Schedule generation on top of the library's public ``Scheduler`` API.

Nothing here reimplements solver logic. This module prepares a validated run
configuration, drives ``Scheduler.get_models()``, and classifies what happened into
one of four outcomes so the command layer can report each case distinctly.
"""

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError
from scheduler import CombinedConfig, OptimizerFlags, Scheduler
from scheduler.models import CourseInstance

DEFAULT_SOLVER_TIMEOUT_MS = 60_000
"""Per-check Z3 timeout applied to every run so one hard problem cannot hang the shell."""

REASON_EXHAUSTED = "solution_space_exhausted"
REASON_TIMEOUT = "solver_timeout"
REASON_UNKNOWN = "solver_unknown"

_REASON_TEXT = {
    REASON_EXHAUSTED: "the solution space is exhausted",
    REASON_TIMEOUT: "the solver timed out",
    REASON_UNKNOWN: "the solver could not decide",
}

Schedule = list[CourseInstance]
ProgressCallback = Callable[[int, int], None]
"""Called as ``callback(found_so_far, limit)`` after each schedule arrives."""


class SchedulerLike(Protocol):
    """The slice of ``scheduler.Scheduler`` this module relies on."""

    def get_models(self) -> Iterator[Schedule]: ...


SchedulerFactory = Callable[..., SchedulerLike]
"""``factory(config, *, solver_timeout_ms=...)``; defaults to ``scheduler.Scheduler``."""


@dataclass(frozen=True)
class GenerationResult:
    """The generated set plus the settings that produced it."""

    schedules: list[Schedule]
    limit: int
    optimizer_flags: tuple[OptimizerFlags, ...]
    completion_reason: str | None
    """``None`` when the limit was reached; otherwise one of the ``REASON_*`` constants."""
    generated_at: datetime
    config_path: Path | None = None

    @property
    def count(self) -> int:
        return len(self.schedules)

    @property
    def reached_limit(self) -> bool:
        return self.count >= self.limit


@dataclass(frozen=True)
class GenerationSuccess:
    result: GenerationResult


@dataclass(frozen=True)
class NoFeasibleSchedule:
    reason: str
    """One of the ``REASON_*`` constants."""


@dataclass(frozen=True)
class InvalidConfiguration:
    errors: tuple[str, ...]


@dataclass(frozen=True)
class GenerationFailed:
    message: str
    exception: BaseException | None = None


GenerationOutcome = GenerationSuccess | NoFeasibleSchedule | InvalidConfiguration | GenerationFailed


def describe_reason(reason: str | None) -> str:
    """Human wording for a completion reason, for use inside a sentence."""
    if reason is None:
        return "the limit was reached"
    return _REASON_TEXT.get(reason, reason)


def resolve_optimizer_flags(
    config: CombinedConfig, optimize: bool | None
) -> tuple[OptimizerFlags, ...]:
    """Decide which optimizer flags a run uses.

    * ``None``: the configuration's own flags, unchanged.
    * ``False``: no optimization.
    * ``True``: the configuration's flags, or every flag when the configuration lists none.
    """
    if optimize is None:
        return tuple(config.optimizer_flags)
    if not optimize:
        return ()
    return tuple(config.optimizer_flags) or tuple(OptimizerFlags)


def prepare_run_config(
    config: CombinedConfig, *, limit: int | None = None, optimize: bool | None = None
) -> CombinedConfig:
    """Return a freshly validated copy of ``config`` with the run's limit and flags applied.

    The original object is never mutated, so a failed run leaves the session's
    configuration intact. Validation runs against the complete configuration.

    Raises:
        pydantic.ValidationError: the resulting configuration is not valid.
    """
    data = config.model_dump(mode="python")
    if limit is not None:
        data["limit"] = limit
    data["optimizer_flags"] = list(resolve_optimizer_flags(config, optimize))
    return CombinedConfig.model_validate(data)


def format_validation_errors(exc: ValidationError) -> tuple[str, ...]:
    """One ``location: message`` line per Pydantic error."""
    lines = []
    for error in exc.errors(include_url=False):
        location = ".".join(str(part) for part in error["loc"]) or "config"
        lines.append(f"{location}: {error['msg']}")
    return tuple(lines)


def generate_schedules(
    config: CombinedConfig | None,
    *,
    limit: int | None = None,
    optimize: bool | None = None,
    solver_timeout_ms: int | None = DEFAULT_SOLVER_TIMEOUT_MS,
    on_progress: ProgressCallback | None = None,
    scheduler_factory: SchedulerFactory = Scheduler,
    config_path: Path | None = None,
) -> GenerationOutcome:
    """Generate schedules from ``config`` and classify the outcome.

    Args:
        config: the session's configuration. ``None`` is reported as invalid.
        limit: overrides the configuration's ``limit`` for this run only.
        optimize: see :func:`resolve_optimizer_flags`.
        solver_timeout_ms: per-check Z3 timeout; ``None`` disables it.
        on_progress: called after each schedule so a slow solve can show progress.
        scheduler_factory: injection point for tests; must accept the ``Scheduler`` signature.
        config_path: recorded on the result for display purposes.
    """
    if config is None:
        return InvalidConfiguration(("No configuration is loaded.",))
    try:
        run_config = prepare_run_config(config, limit=limit, optimize=optimize)
    except ValidationError as exc:
        return InvalidConfiguration(format_validation_errors(exc))

    schedules: list[Schedule] = []
    try:
        scheduler = scheduler_factory(run_config, solver_timeout_ms=solver_timeout_ms)
        for schedule in scheduler.get_models():
            schedules.append(schedule)
            if on_progress is not None:
                on_progress(len(schedules), run_config.limit)
    except Exception as exc:
        # z3.Z3Exception and friends share no useful base class; anything raised while
        # constructing or driving the solver is an unexpected runtime failure.
        return GenerationFailed(f"{type(exc).__name__}: {exc}", exc)

    reason = _completion_reason(scheduler)
    if not schedules:
        return NoFeasibleSchedule(reason or REASON_UNKNOWN)
    return GenerationSuccess(
        GenerationResult(
            schedules=schedules,
            limit=run_config.limit,
            optimizer_flags=tuple(run_config.optimizer_flags),
            completion_reason=reason,
            generated_at=datetime.now(),
            config_path=config_path,
        )
    )


def _completion_reason(scheduler: Any) -> str | None:
    # The library records why enumeration stopped on a private property that its own
    # REST adapter reads. There is no public accessor that avoids a second solve, so
    # read it defensively and treat anything unexpected as unknown.
    reason = getattr(scheduler, "_enumeration_completion_reason", None)
    return reason if isinstance(reason, str) else None


def quiet_library_logging() -> None:
    """Keep the library's own log lines (for example ``No solution found``) off the console.

    The shell reports every outcome itself, so the library's messages would only duplicate
    or contradict them. Applications that want the library's logging can configure the
    ``Scheduler`` logger themselves.
    """
    library_logger = logging.getLogger("Scheduler")
    library_logger.addHandler(logging.NullHandler())
    library_logger.propagate = False
