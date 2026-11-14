"""How a schedule writes its days and times, so every view of a schedule reads the same.

Used by the GUI's schedule views and exports (``model/schedules.py``) and by the shell's
``display`` command (``commands/display_schedules.py``).
"""

from scheduler.models import Day

DAY_NAMES: dict[int, str] = {day.value: day.name for day in Day}
"""The library's day numbers and their names: ``{1: "MON", ..., 5: "FRI"}``."""


def clock_text(minutes: int) -> str:
    """Minutes after midnight as ``HH:MM``; for example, ``480`` is ``"08:00"``."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
