"""Export generated schedules to JSON or CSV with the library's writers.

Overwrite protection
--------------------
``export_schedules`` never replaces an existing file unless ``overwrite=True``. When
``overwrite`` is false it claims the path with an exclusive create (``open(path, "x")``),
so the check and the create are one atomic step and a file that appears between a prompt
and the write is still refused with :class:`FileExistsError`. The command layer turns that
error into a yes/no confirmation. If the write then fails, the claimed empty file is removed
so a failed export leaves no half-written output behind.
"""

import os
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scheduler.writers import CSVWriter, JSONWriter

from zimpasta.generate import Schedule


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"

    @classmethod
    def parse(cls, text: str) -> "ExportFormat | None":
        """Case-insensitive lookup; ``None`` when ``text`` names no supported format."""
        try:
            return cls(text.strip().lower())
        except ValueError:
            return None

    @property
    def extension(self) -> str:
        return f".{self.value}"


@dataclass(frozen=True)
class ExportResult:
    path: Path
    format: ExportFormat
    schedule_count: int
    overwrote: bool


def resolve_output_path(name: str, fmt: ExportFormat) -> Path:
    """Absolute path for a user-typed name, adding the format's extension when missing."""
    path = Path(name.strip()).expanduser()
    if path.suffix.lower() != fmt.extension:
        path = path.with_name(path.name + fmt.extension)
    return path.resolve()


def unwritable_reason(path: Path) -> str | None:
    """Why ``path`` cannot be written, or ``None`` when it looks writable."""
    if path.is_dir():
        return "the name refers to a directory"
    parent = path.parent
    if not parent.is_dir():
        return "the directory does not exist"
    if path.exists():
        return None if os.access(path, os.W_OK) else "the file is read-only"
    return None if os.access(parent, os.W_OK) else "the directory is not writable"


def export_schedules(
    schedules: Iterable[Schedule],
    path: Path,
    fmt: ExportFormat,
    *,
    overwrite: bool = False,
) -> ExportResult:
    """Write ``schedules`` to ``path`` as UTF-8 in the given format.

    Raises:
        ValueError: ``schedules`` is empty.
        FileExistsError: ``path`` exists and ``overwrite`` is false.
        OSError: the file cannot be created or written.
    """
    schedules = list(schedules)
    if not schedules:
        raise ValueError("There are no schedules to export.")

    existed = path.exists()
    claimed = False
    if not overwrite:
        with open(path, "x", encoding="utf-8"):
            pass
        claimed = True

    writer = JSONWriter(str(path)) if fmt is ExportFormat.JSON else CSVWriter(str(path))
    try:
        with writer as active:
            for schedule in schedules:
                active.add_schedule(schedule)
    except BaseException:
        if claimed:
            path.unlink(missing_ok=True)
        raise
    return ExportResult(path=path, format=fmt, schedule_count=len(schedules), overwrote=existed)
