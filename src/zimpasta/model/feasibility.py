"""Problems that keep a valid configuration from having any schedule, found without solving.

The library's input checks accept a configuration when every rule about its input holds,
but some combinations still leave nothing to schedule: disable the only class pattern
that puts a faculty member on their mandatory day, and generation finds no schedule
without saying why. The library's diagnostics find these "preflight" problems with a
quick static analysis (well under a second), so the workspace runs it after every change
and the editor's banner lists them as warnings.

This uses the library's ``DiagnosticEngine`` analyses directly, which are not part of
its public API (``Scheduler.diagnose()`` is, but it also runs the solver and takes
seconds). Those analyses need only the normalized problem, not the solver's artifacts.
tests/model/test_feasibility.py fails if a library upgrade changes them.
"""

from types import SimpleNamespace

from scheduler import CombinedConfig
from scheduler.diagnostics import DiagnosticEngine
from scheduler.problem import SchedulingProblem

from zimpasta.model.issues import COLLECTIONS, Issue

NOTES = frozenset({"derived_faculty_candidates"})
"""Findings that are notes, not problems ("derives faculty candidates from preferences")."""

UNAVAILABLE = "faculty_candidate_unavailable"
"""Reported for each candidate on its own ("Rogers has no available compatible meeting
pattern for CMSC 161.02"). It only rules out a schedule when it holds for every candidate."""

_NO_SOLVER = SimpleNamespace(context=None, relations=None, diagnostic_constraints=None)
"""Stands in for the solver's artifacts, which the static analyses don't use."""

_AREAS = {location: area for area, location in COLLECTIONS.items()}


def schedule_problems(config: CombinedConfig) -> tuple[Issue, ...]:
    """What keeps ``config`` from having any schedule, as far as can be told without solving.

    Empty does not promise a schedule exists; the solver can still find conflicts that
    only show up in combination. Never raises: these are advisory, so a failure here
    must not block an edit.
    """
    try:
        engine = DiagnosticEngine(SchedulingProblem.from_config(config), _NO_SOLVER)
        domains = engine._candidate_domains()
        findings = engine._preflight_findings(domains, engine._capacity_analysis())
    except Exception:
        return ()

    candidates = {domain.course: set(domain.faculty_candidates) for domain in domains}
    unavailable: dict[str, set[str]] = {}
    for finding in findings:
        if finding.kind == UNAVAILABLE:
            course, faculty = finding.subjects[:2]
            unavailable.setdefault(course, set()).add(faculty)

    def rules_out_every_schedule(finding) -> bool:
        if finding.kind in NOTES:
            return False
        if finding.kind == UNAVAILABLE:
            course = finding.subjects[0]
            return unavailable[course] >= candidates.get(course, set())
        return True

    return tuple(
        _issue(finding.code or finding.kind, finding.message, finding.locations)
        for finding in findings
        if rules_out_every_schedule(finding)
    )


def _issue(code: str, message: str, locations: tuple[str, ...]) -> Issue:
    """Located at the first configuration item the finding points at, if any."""
    for pointer in locations:
        parts = pointer.strip("/").split("/")
        area = _AREAS.get(tuple(parts[:2]))
        if area is None:
            continue
        index = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        field = ".".join(parts[3:]) or None
        return Issue(".".join(parts), code, message, area, index, field)
    return Issue("config", code, message)
