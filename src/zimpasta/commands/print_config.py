"""The ``print`` command: show the loaded configuration in human-readable form.

Usage: ``print``. Takes no arguments.

Author: Foster VanFleet. Converted to the command model.
"""

from collections.abc import Iterable, Sequence

from scheduler import CombinedConfig, TimeSlotConfig

from zimpasta.command import CommandSpec, Invocation
from zimpasta.console import Console
from zimpasta.session import Session

NO_CONFIG = "No configuration is loaded."


def print_config(console: Console, session: Session, invocation: Invocation) -> None:
    """Handler: print the loaded configuration section by section."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    for line in _lines(session.config):
        console.say(line)


def _lines(config: CombinedConfig) -> list[str]:
    """The whole printout, one string per line."""
    items = config.config
    return [
        "Configuration",
        "=" * len("Configuration"),
        *_rooms_or_labs("Rooms", items.rooms),
        *_rooms_or_labs("Labs", items.labs),
        *_courses(items.courses),
        *_faculty(items.faculty),
        *_time_slots(config.time_slot_config),
        "",
        f"Schedule Limit: {config.limit}",
        f"Optimizer Flags: {_listed([str(flag) for flag in config.optimizer_flags])}",
    ]


def _heading(title: str) -> list[str]:
    """A blank line, then ``title`` underlined with dashes."""
    return ["", title, "-" * len(title)]


def _listed(values: Iterable[str] | None) -> str:
    """``values`` separated by commas, or ``None`` when there are none."""
    return ", ".join(values) if values else "None"


def _rooms_or_labs(title: str, resources: Sequence) -> list[str]:
    lines = _heading(title)
    for resource in resources:
        lines += [
            resource.name,
            f"  Capacity: {resource.capacity}",
            f"  Features: {_listed(resource.features)}",
        ]
    return lines


def _courses(courses: Sequence) -> list[str]:
    lines = _heading("Courses")
    for course in courses:
        lines += [
            course.course_id,
            f"  Credits: {course.credits}",
            f"  Capacity: {course.capacity}",
            f"  Rooms: {_listed(course.room)}",
            f"  Labs: {_listed(course.lab)}",
            f"  Conflicts: {_listed(course.conflicts)}",
            f"  Faculty: {_listed(course.faculty)}",
        ]
    return lines


def _faculty(faculty: Sequence) -> list[str]:
    lines = _heading("Faculty")
    for member in faculty:
        lines += [
            member.name,
            f"  Credits: {member.minimum_credits}-{member.maximum_credits}",
            f"  Unique course limit: {member.unique_course_limit}",
            "  Availability:",
        ]
        for day, times in member.times.items():
            lines.append(f"    {day}: " + ", ".join(f"{time.start}-{time.end}" for time in times))
    return lines


def _time_slots(slots: TimeSlotConfig) -> list[str]:
    lines = [*_heading("Time Slots"), "Available Times:"]
    for day, blocks in slots.times.items():
        for block in blocks:
            lines.append(f"  {day}: {block.start}-{block.end} ({block.spacing} minute spacing)")
    lines += ["", "Class Patterns:"]
    for pattern in slots.classes:
        lines.append(f"  {pattern.credits} credits")
        for meeting in pattern.meetings:
            lab = ", lab" if meeting.lab else ""
            lines.append(f"    {meeting.day}, {meeting.duration} minutes{lab}")
    return [
        *lines,
        "",
        f"Maximum time gap: {slots.max_time_gap} minutes",
        f"Minimum time overlap: {slots.min_time_overlap} minutes",
    ]


SPECS = (
    CommandSpec(
        "print",
        description="Print the loaded configuration",
        handler=print_config,
    ),
)
