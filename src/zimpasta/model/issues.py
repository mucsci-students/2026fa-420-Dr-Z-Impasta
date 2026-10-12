"""Validation problems in a form a view can show next to the field that caused them.

The scheduler library reports problems as Pydantic ``ValidationError`` locations such as
``("config", "faculty", 0, "minimum_credits")``. :func:`issues_from_error` keeps the
library's code and message and adds where the problem is in editor terms: which area
(``"faculty"``), which item in it (``0``), and which field (``"minimum_credits"``).
Nothing here decides whether something is valid; the library always does that.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

COLLECTIONS: dict[str, tuple[str, str]] = {
    "rooms": ("config", "rooms"),
    "labs": ("config", "labs"),
    "courses": ("config", "courses"),
    "faculty": ("config", "faculty"),
    "patterns": ("time_slot_config", "classes"),
}
"""Editor area name -> where that list lives in a ``CombinedConfig`` document."""

_AREA_BY_LOCATION = {location: area for area, location in COLLECTIONS.items()}

REQUIRED_LISTS = ("rooms", "courses", "faculty")
"""Areas the library requires at least one item in. A new configuration starts without them."""

_MISSING_ITEM_MESSAGES = {
    "rooms": "Add at least one room.",
    "courses": "Add at least one course.",
    "faculty": "Add at least one faculty member.",
}

_MESSAGE_PREFIXES = ("Value error, ", "Assertion failed, ")


@dataclass(frozen=True)
class Issue:
    """One problem the library found, located for display."""

    path: str
    """Dotted library location, for example ``config.faculty.0.minimum_credits``."""

    code: str
    """The library's error type, for example ``faculty_minimum_exceeds_maximum_credits``."""

    message: str
    """Human-readable explanation from the library."""

    area: str | None = None
    """``rooms``, ``labs``, ``courses``, ``faculty``, ``patterns``, ``time_slots``,
    ``settings``, or ``None`` when the problem is about the configuration as a whole."""

    index: int | None = None
    """Position of the item within ``area``, when the problem belongs to one item."""

    field: str | None = None
    """Dotted field path inside the item or section, for example ``meetings.0.duration``."""

    @property
    def is_missing_required_item(self) -> bool:
        """Whether this only says a required list (rooms, courses, faculty) is still empty."""
        return (
            self.code == "too_short"
            and self.index is None
            and self.field is None
            and self.area in REQUIRED_LISTS
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "code": self.code,
            "message": self.message,
            "area": self.area,
            "index": self.index,
            "field": self.field,
        }


def issues_from_error(error: ValidationError) -> list[Issue]:
    """Every problem in ``error``, in the order the library reported them."""
    return [_issue(detail) for detail in error.errors(include_url=False)]


def issue(message: str, *, code: str = "invalid", path: str = "", **where) -> Issue:
    """An issue raised by this application rather than the library, such as a wrong type."""
    return Issue(path=path, code=code, message=message, **where)


def _issue(detail: dict) -> Issue:
    location = tuple(detail.get("loc", ()))
    area, index, field = locate(location)
    code = str(detail.get("type", "invalid"))
    message = str(detail.get("msg", "Invalid value."))
    for prefix in _MESSAGE_PREFIXES:
        if message.startswith(prefix):
            message = message[len(prefix) :]
            break
    if code == "too_short" and index is None and field is None and area in REQUIRED_LISTS:
        message = _MISSING_ITEM_MESSAGES[area]
    return Issue(
        path=".".join(str(part) for part in location),
        code=code,
        message=message,
        area=area,
        index=index,
        field=field,
    )


def locate(location: Sequence[str | int]) -> tuple[str | None, int | None, str | None]:
    """Translate a library location into ``(area, index, field)``."""
    parts = tuple(location)
    if len(parts) >= 2 and parts[:2] in _AREA_BY_LOCATION:
        area = _AREA_BY_LOCATION[parts[:2]]
        rest = parts[2:]
        if rest and isinstance(rest[0], int):
            return area, rest[0], _join(rest[1:])
        return area, None, _join(rest)
    if parts[:1] == ("time_slot_config",):
        return "time_slots", None, _join(parts[1:])
    if parts[:1] in (("limit",), ("optimizer_flags",)):
        return "settings", None, str(parts[0])
    return None, None, _join(parts)


def _join(parts: Sequence[str | int]) -> str | None:
    return ".".join(str(part) for part in parts) or None
