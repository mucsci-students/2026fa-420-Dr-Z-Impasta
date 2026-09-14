"""Delete a room, lab, course, or faculty member from the loaded configuration.

``delete course "CS 101"`` runs straight away; a bare ``delete``, or one missing the
item, asks which category and which item through numbered menus. Either way the handler
confirms before touching the configuration.

Deleting an item also strips every reference to it, because the library rejects a
configuration whose courses or faculty point at a name that no longer exists. The
references are cleared before the item itself is removed: ``validate_assignment``
re-runs cross-reference validation on every assignment, so removing the item first
would fail against references that are about to be cleaned up anyway.
"""

from pydantic import ValidationError

from zimpasta.command import CommandSpec, Invocation, Positional
from zimpasta.console import Console
from zimpasta.prompts import ask_menu, ask_yes_no
from zimpasta.session import Session

NO_CONFIG = "No configuration loaded. Load one first."
NOTHING_TO_DELETE = "There is nothing of that type to delete."
NOT_FOUND = "There is no {kind} named {name}."
CANCELLED = "Cancelled. Nothing was deleted."
DELETED = "Deleted {name}."
WOULD_LEAVE_INVALID = "Can't delete {name}: {error}"

CANCEL = "Cancel"

KINDS: tuple[str, ...] = ("course", "room", "lab", "faculty")
"""Categories, in the order the placeholder grammar and ``help`` list them."""


def _names(scheduler, kind: str) -> list[str]:
    """Names of every item of ``kind``, in display order."""
    if kind == "room":
        return [room.name for room in scheduler.rooms]
    if kind == "lab":
        return [lab.name for lab in scheduler.labs]
    if kind == "course":
        return [course.course_id for course in scheduler.courses]
    return [faculty.name for faculty in scheduler.faculty]


def _remove_room(scheduler, name: str) -> None:
    for course in scheduler.courses:
        course.room = [room for room in course.room if room != name]
    for faculty in scheduler.faculty:
        faculty.room_preferences = {
            room: rank for room, rank in faculty.room_preferences.items() if room != name
        }
    scheduler.rooms = [room for room in scheduler.rooms if room.name != name]


def _remove_lab(scheduler, name: str) -> None:
    for course in scheduler.courses:
        course.lab = [lab for lab in course.lab if lab != name]
    for faculty in scheduler.faculty:
        faculty.lab_preferences = {
            lab: rank for lab, rank in faculty.lab_preferences.items() if lab != name
        }
    scheduler.labs = [lab for lab in scheduler.labs if lab.name != name]


def _remove_course(scheduler, name: str) -> None:
    for course in scheduler.courses:
        course.conflicts = [conflict for conflict in course.conflicts if conflict != name]
    for faculty in scheduler.faculty:
        faculty.course_preferences = {
            course: rank for course, rank in faculty.course_preferences.items() if course != name
        }
    scheduler.courses = [course for course in scheduler.courses if course.course_id != name]


def _remove_faculty(scheduler, name: str) -> None:
    for course in scheduler.courses:
        if course.faculty is not None:
            # An empty candidate list is rejected; None means "derive from preferences".
            course.faculty = [member for member in course.faculty if member != name] or None
    scheduler.faculty = [faculty for faculty in scheduler.faculty if faculty.name != name]


_REMOVERS = {
    "room": _remove_room,
    "lab": _remove_lab,
    "course": _remove_course,
    "faculty": _remove_faculty,
}


def build(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    """Ask which category and which item, listing only what the configuration holds."""
    if session.config is None:
        console.say(NO_CONFIG)
        return None

    kind = invocation.get("kind")
    if kind is None:
        choice = ask_menu(console, "Delete what?", [*KINDS, CANCEL])
        if choice == len(KINDS) + 1:
            console.say(CANCELLED)
            return None
        kind = KINDS[choice - 1]

    if invocation.get("id") is not None:
        return invocation.with_values({"kind": str(kind)})

    names = _names(session.config.config, str(kind))
    if not names:
        console.say(NOTHING_TO_DELETE)
        return None
    choice = ask_menu(console, f"Delete which {kind}?", [*names, CANCEL])
    if choice == len(names) + 1:
        console.say(CANCELLED)
        return None
    return invocation.with_values({"kind": str(kind), "id": names[choice - 1]})


def delete(console: Console, session: Session, invocation: Invocation) -> None:
    """Confirm, then remove the item and every reference to it."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    config = session.config
    kind = str(invocation.get("kind"))
    name = str(invocation.get("id"))

    if name not in _names(config.config, kind):
        console.say(NOT_FOUND.format(kind=kind, name=name))
        return

    if not ask_yes_no(console, f"Delete {kind} '{name}'? (yes/no): "):
        console.say(CANCELLED)
        return

    try:
        with config.edit_mode() as working:
            _REMOVERS[kind](working.config, name)
    except ValidationError as error:
        console.say(WOULD_LEAVE_INVALID.format(name=name, error=error))
        return

    console.say(DELETED.format(name=name))


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "delete",
        positionals=(Positional("kind", choices=KINDS), Positional("id")),
        description="Remove an item",
        handler=delete,
        builder=build,
    ),
)
