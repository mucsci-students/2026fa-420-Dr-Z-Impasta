"""The schedules available to the viewer: generated or imported, with export and views.

Schedules are kept in the scheduler library's JSON output form, the format its
``JSONWriter`` writes: a list of schedules, each a list of course assignments shaped like
:class:`scheduler.json_types.CourseInstanceJSON`::

    [[{"course": "CS 101.01", "faculty": "Dr. Smith", "room": "Room 101",
       "times": [{"day": 1, "start": 840, "duration": 150, "delivery": "in_person"}],
       "reserve_room_during_lab": true}, ...], ...]

``day`` is 1 (Monday) to 5 (Friday); ``start`` and ``duration`` are minutes; ``lab`` and
``lab_index`` are present only for sections with a lab, and ``lab_index`` marks which
meeting is the lab. Keeping this one form means generated and imported schedules behave
the same, exports load back unchanged, and files from the library's own CLI load too.

Import accepts a list of schedules or a single schedule (a list of assignments) and
validates it with the library's TypedDicts before replacing anything. JSON export is
byte-for-byte what ``JSONWriter`` writes; CSV export matches ``CSVWriter`` line for line.
"""

import copy
import csv
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath

from pydantic import TypeAdapter, ValidationError
from scheduler.json_types import CourseInstanceJSON
from scheduler.models import CourseInstance, Day

from zimpasta.model.generate import GenerationResult
from zimpasta.model.issues import Issue

Assignment = dict
"""One ``CourseInstanceJSON`` record."""

_SCHEDULE = TypeAdapter(list[CourseInstanceJSON])
_DAY_NAMES = {day.value: day.name for day in Day}
_MINUTES_PER_DAY = 24 * 60

GROUPINGS = ("room", "faculty")
FORMATS = ("json", "csv")

_GROUP_ORDER = {"room": 0, "lab": 1, "online": 2, "unassigned": 3, "faculty": 0}


class ScheduleError(Exception):
    code = "schedule_error"

    def __init__(self, message: str, *, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message)
        self.message = message
        self.issues = issues


class InvalidScheduleFile(ScheduleError):
    def __init__(self, code: str, message: str, *, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message, issues=issues)
        self.code = code


class NoSchedules(ScheduleError):
    code = "no_schedules"

    def __init__(self) -> None:
        super().__init__("No schedules yet. Generate schedules or load a schedule JSON file.")


class ScheduleNotFound(ScheduleError):
    code = "not_found"


@dataclass(frozen=True)
class ExportedSchedules:
    content: str
    filename: str
    media_type: str
    count: int


def to_assignment(instance: CourseInstance) -> Assignment:
    """One generated assignment in the exact form ``JSONWriter`` writes."""
    return json.loads(json.dumps(instance.model_dump(by_alias=True, exclude_none=True)))


class ScheduleSet:
    """The current schedules and where they came from. Replaced as a whole, never merged."""

    def __init__(self, *, clock: Callable[[], datetime] = datetime.now) -> None:
        self._clock = clock
        self._schedules: list[list[Assignment]] = []
        self._source: str | None = None
        self._name: str | None = None
        self._created_at: datetime | None = None
        self._details: dict = {}

    @property
    def count(self) -> int:
        return len(self._schedules)

    @property
    def source(self) -> str | None:
        """``generated``, ``imported``, or ``None`` when empty."""
        return self._source

    def schedules(self) -> list[list[Assignment]]:
        return copy.deepcopy(self._schedules)

    def schedule(self, number: int) -> list[Assignment]:
        """Schedule ``number``, counting from 1."""
        return copy.deepcopy(self._get(number))

    # ----------------------------------------------------------- replacing

    def replace_generated(
        self, result: GenerationResult, *, config_name: str | None = None
    ) -> None:
        self._set(
            [[to_assignment(instance) for instance in schedule] for schedule in result.schedules],
            source="generated",
            name=config_name,
            details={
                "limit": result.limit,
                "optimizer_flags": [flag.value for flag in result.optimizer_flags],
                "completion_reason": result.completion_reason,
            },
        )

    def import_text(self, text: str, *, filename: str) -> int:
        """Replace the schedules with those in a JSON file, if it is valid. Returns the count.

        Raises:
            InvalidScheduleFile: the text is not JSON or not in the schedule format. The
                current schedules are kept.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidScheduleFile(
                "malformed_json",
                f"{filename} is not valid JSON: {error.msg} "
                f"(line {error.lineno}, column {error.colno}).",
            ) from None
        schedules = _parse_schedules(data, filename)
        self._set(schedules, source="imported", name=filename, details={})
        return len(schedules)

    def clear(self) -> None:
        self._set([], source=None, name=None, details={})
        self._created_at = None

    # ------------------------------------------------------------ exporting

    def export(self, which: str | int = "all", fmt: str = "json") -> ExportedSchedules:
        """The chosen schedules as UTF-8 text in the library's JSON or CSV format.

        ``which`` is ``"all"`` or a schedule number. A single schedule is exported as a
        one-element list so every JSON export has the same shape and loads back.
        """
        if fmt not in FORMATS:
            raise ScheduleError(f"Unknown format {fmt!r}. Use json or csv.")
        if which == "all":
            if not self._schedules:
                raise NoSchedules()
            chosen = self._schedules
            stem = "schedules"
        else:
            chosen = [self._get(_number(which))]
            stem = f"schedule-{_number(which)}"
        base = PurePath(self._name).stem if self._name else None
        if base and self._source == "generated":
            stem = f"{base}-{stem}"
        if fmt == "json":
            content = json.dumps(chosen, separators=(",", ":"))
            return ExportedSchedules(content, f"{stem}.json", "application/json", len(chosen))
        content = "\n\n".join(
            "\n".join(_csv_row(assignment) for assignment in schedule) for schedule in chosen
        )
        return ExportedSchedules(content, f"{stem}.csv", "text/csv", len(chosen))

    # -------------------------------------------------------------- viewing

    def summary(self) -> dict:
        """Counts and provenance for the viewer header and the generator's result list."""
        return {
            "count": self.count,
            "source": self._source,
            "name": self._name,
            "created_at": self._created_at.isoformat(timespec="seconds")
            if self._created_at
            else None,
            **self._details,
            "schedules": [
                {"number": number, **_totals(schedule)}
                for number, schedule in enumerate(self._schedules, start=1)
            ],
        }

    def view(self, number: int, group: str = "room") -> dict:
        """Schedule ``number`` grouped by room and lab, or by faculty member."""
        if group not in GROUPINGS:
            raise ScheduleError(f"Unknown grouping {group!r}. Use room or faculty.")
        number = _number(number)
        schedule = self._get(number)
        groups = by_room(schedule) if group == "room" else by_faculty(schedule)
        return {
            "number": number,
            "count": self.count,
            "group": group,
            "totals": _totals(schedule),
            "groups": groups,
        }

    # ----------------------------------------------------------- internals

    def _set(self, schedules, *, source, name, details) -> None:
        self._schedules = schedules
        self._source = source
        self._name = name
        self._details = details
        self._created_at = self._clock()

    def _get(self, number: int) -> list[Assignment]:
        if not self._schedules:
            raise NoSchedules()
        if not 1 <= number <= len(self._schedules):
            raise ScheduleNotFound(
                f"There is no schedule {number}. Choose 1 to {len(self._schedules)}."
            )
        return self._schedules[number - 1]


# --------------------------------------------------------------------- views


def meetings(assignment: Assignment) -> list[dict]:
    """Every meeting of one assignment, with its day and clock times spelled out."""
    course = assignment["course"]
    course_id, dot, section = course.rpartition(".")
    if not dot:
        course_id, section = course, ""
    lab = assignment.get("lab")
    lab_index = assignment.get("lab_index") if lab is not None else None
    result = []
    for position, time in enumerate(assignment["times"]):
        start, duration = time["start"], time["duration"]
        result.append(
            {
                "course": course,
                "course_id": course_id,
                "section": section,
                "faculty": assignment["faculty"],
                "room": assignment.get("room"),
                "lab": lab,
                "day": _DAY_NAMES[time["day"]],
                "day_number": time["day"],
                "start": start,
                "end": start + duration,
                "start_time": _clock_text(start),
                "end_time": _clock_text(start + duration),
                "duration": duration,
                "kind": "lab" if position == lab_index else "lecture",
                "delivery": time.get("delivery", "in_person"),
                "reserve_room_during_lab": assignment.get("reserve_room_during_lab", True),
            }
        )
    return result


def by_room(schedule: list[Assignment]) -> list[dict]:
    """Meetings grouped by the room or lab they physically occupy.

    A lab meeting belongs to its lab, and also to the section's room when the section
    keeps its room reserved during the lab (marked ``room_held_for_lab``). Online
    meetings are grouped under "Online".
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for assignment in schedule:
        for meeting in meetings(assignment):
            other = {"other": meeting["faculty"], "other_label": "Faculty"}
            if meeting["delivery"] == "online":
                _add(groups, ("online", "Online"), {**meeting, **other})
            elif meeting["kind"] == "lab":
                _add(groups, ("lab", meeting["lab"]), {**meeting, **other})
                if meeting["reserve_room_during_lab"] and meeting["room"]:
                    _add(
                        groups,
                        ("room", meeting["room"]),
                        {**meeting, **other, "room_held_for_lab": True},
                    )
            elif meeting["room"]:
                _add(groups, ("room", meeting["room"]), {**meeting, **other})
            else:
                _add(groups, ("unassigned", "No room"), {**meeting, **other})
    return _finish(groups)


def by_faculty(schedule: list[Assignment]) -> list[dict]:
    """Meetings grouped by faculty member, each showing where it meets."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for assignment in schedule:
        for meeting in meetings(assignment):
            if meeting["delivery"] == "online":
                where = "Online"
            elif meeting["kind"] == "lab":
                where = meeting["lab"]
            else:
                where = meeting["room"] or "No room"
            _add(
                groups,
                ("faculty", meeting["faculty"]),
                {**meeting, "other": where, "other_label": "Room / lab"},
            )
    return _finish(groups)


def _add(groups: dict, key: tuple[str, str], meeting: dict) -> None:
    meeting.setdefault("room_held_for_lab", False)
    groups.setdefault(key, []).append(meeting)


def _finish(groups: dict[tuple[str, str], list[dict]]) -> list[dict]:
    result = []
    for (kind, name), items in sorted(
        groups.items(), key=lambda entry: (_GROUP_ORDER[entry[0][0]], entry[0][1])
    ):
        items.sort(key=lambda meeting: (meeting["day_number"], meeting["start"], meeting["course"]))
        result.append(
            {
                "name": name,
                "kind": kind,
                "sections": len({meeting["course"] for meeting in items}),
                "meeting_count": len(items),
                "meetings": items,
            }
        )
    return result


def _totals(schedule: list[Assignment]) -> dict:
    return {
        "sections": len(schedule),
        "faculty": len({assignment["faculty"] for assignment in schedule}),
        "rooms": len({assignment["room"] for assignment in schedule if assignment.get("room")}),
        "labs": len({assignment["lab"] for assignment in schedule if assignment.get("lab")}),
    }


# ------------------------------------------------------------- file format


def _parse_schedules(data: object, filename: str) -> list[list[Assignment]]:
    if not isinstance(data, list):
        raise InvalidScheduleFile(
            "invalid_schedule_file",
            f"{filename} is not a schedule file: expected a JSON list of schedules.",
        )
    if not data:
        raise InvalidScheduleFile("invalid_schedule_file", f"{filename} contains no schedules.")
    single = all(isinstance(entry, dict) for entry in data)
    candidates = [data] if single else data
    schedules: list[list[Assignment]] = []
    issues: list[Issue] = []
    for position, candidate in enumerate(candidates):
        prefix = () if single else (position,)
        try:
            validated = _SCHEDULE.validate_python(candidate)
        except ValidationError as error:
            issues.extend(_schedule_issue(prefix, detail) for detail in error.errors())
            continue
        issues.extend(_format_issues(prefix, validated))
        schedules.append(json.loads(json.dumps(validated)))
    if issues:
        count = len(issues)
        raise InvalidScheduleFile(
            "invalid_schedule_file",
            f"{filename} is not in the schedule format: {count} "
            f"{'problem' if count == 1 else 'problems'} found.",
            issues=tuple(issues[:50]),
        )
    return schedules


def _format_issues(prefix: tuple, schedule: list[dict]) -> list[Issue]:
    """Checks the TypedDicts can't express: days, clock ranges, and the lab index."""
    problems = []
    for row, assignment in enumerate(schedule):
        times = assignment["times"]
        for column, time in enumerate(times):
            where = (*prefix, row, "times", column)
            if time["day"] not in _DAY_NAMES:
                problems.append(_problem((*where, "day"), "Day must be 1 (Monday) to 5 (Friday)."))
            if not 0 <= time["start"] < _MINUTES_PER_DAY:
                problems.append(
                    _problem((*where, "start"), "Start must be minutes after midnight.")
                )
            if time["duration"] <= 0 or time["start"] + time["duration"] > _MINUTES_PER_DAY:
                problems.append(
                    _problem((*where, "duration"), "Duration must be positive and end that day.")
                )
        lab_index = assignment.get("lab_index")
        if lab_index is not None and not 0 <= lab_index < len(times):
            problems.append(
                _problem((*prefix, row, "lab_index"), "lab_index must point at one of the times.")
            )
    return problems


def _schedule_issue(prefix: tuple, detail: dict) -> Issue:
    return _problem((*prefix, *detail.get("loc", ())), str(detail.get("msg", "Invalid value.")))


def _problem(location: tuple, message: str) -> Issue:
    return Issue(path=".".join(str(part) for part in location), code="invalid", message=message)


def _csv_row(assignment: Assignment) -> str:
    """One assignment as ``CourseInstance.as_csv`` writes it."""
    lab = assignment.get("lab")
    lab_index = assignment.get("lab_index") if lab is not None else None
    times = ",".join(
        f"{_DAY_NAMES[time['day']]} {_clock_text(time['start'])}-"
        f"{_clock_text(time['start'] + time['duration'])}"
        f"{'@online' if time.get('delivery') == 'online' else ''}"
        f"{'^' if position == lab_index else ''}"
        for position, time in enumerate(assignment["times"])
    )
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="").writerow(
        [
            assignment["course"],
            assignment["faculty"],
            assignment.get("room") or "",
            lab or "",
            times,
        ]
    )
    return output.getvalue()


def _clock_text(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _number(value: object) -> int:
    if isinstance(value, bool):
        raise ScheduleNotFound(f"{value!r} is not a schedule number.")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ScheduleNotFound(f"{value!r} is not a schedule number.") from None
