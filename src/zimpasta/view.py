"""Plain-text rendering of generated schedules.

These two functions render the schedules kept in the session, for ``schedules summary`` and
``schedules show``. The ``display`` command is separate: it renders exported CSV and JSON
files from disk (see ``commands/display_schedules.py``).
"""

from scheduler.models import CourseInstance

from zimpasta.generate import GenerationResult, Schedule, describe_reason

_HEADER = ("Course", "Faculty", "Room", "Lab", "Meetings")


def summarize(result: GenerationResult) -> str:
    """Multi-line summary of the generated set."""
    lines = [f"Generated schedules: {result.count} (limit {result.limit})"]
    lines.append(f"Generated at: {result.generated_at:%Y-%m-%d %H:%M:%S}")
    if result.config_path is not None:
        lines.append(f"Configuration: {result.config_path}")
    flags = ", ".join(flag.value for flag in result.optimizer_flags) or "none"
    lines.append(f"Optimizer flags: {flags}")
    if not result.reached_limit:
        lines.append(f"Stopped early: {describe_reason(result.completion_reason)}")
    for number, schedule in enumerate(result.schedules, start=1):
        faculty = {instance.faculty for instance in schedule}
        lines.append(f"  {number}. {len(schedule)} course section(s), {len(faculty)} faculty")
    return "\n".join(lines)


def format_schedule(schedule: Schedule, number: int | None = None) -> str:
    """Aligned table of course, faculty, room, lab, and meeting times for one schedule."""
    rows = [
        (
            instance.course_str,
            instance.faculty,
            instance.room or "-",
            instance.lab or "-",
            _meetings(instance),
        )
        for instance in schedule
    ]
    widths = [len(title) for title in _HEADER]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row, strict=True)]

    def line(cells: tuple[str, ...]) -> str:
        return "  ".join(
            cell.ljust(width) for cell, width in zip(cells, widths, strict=True)
        ).rstrip()

    lines = []
    if number is not None:
        lines.append(f"Schedule {number}")
    lines.append(line(_HEADER))
    lines.append(line(tuple("-" * width for width in widths)))
    lines.extend(line(row) for row in rows)
    return "\n".join(lines)


def _meetings(instance: CourseInstance) -> str:
    parts = []
    for index, meeting in enumerate(instance.times):
        label = str(meeting)
        if instance.lab_index == index:
            label += " (lab)"
        parts.append(label)
    return "; ".join(parts)
