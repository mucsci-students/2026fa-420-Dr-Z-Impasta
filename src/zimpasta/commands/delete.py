"""Delete a room, lab, course, or faculty member from the loaded configuration.

Deleting an item also strips every reference to it, because the library rejects a
configuration whose courses or faculty point at a name that no longer exists. The
references are cleared before the item itself is removed: ``validate_assignment``
re-runs cross-reference validation on every assignment, so removing the item first
would fail against references that are about to be cleaned up anyway.
"""

from pydantic import ValidationError

from zimpasta.console import Console
from zimpasta.prompts import ask_menu, ask_yes_no
from zimpasta.session import Session

NO_CONFIG = "No configuration loaded. Load one first."
NOTHING_TO_DELETE = "There is nothing of that type to delete."
CANCELLED = "Cancelled. Nothing was deleted."
DELETED = "Deleted {name}."
WOULD_LEAVE_INVALID = "Can't delete {name}: {error}"

CANCEL = "Cancel"

_CATEGORIES: tuple[str, ...] = ("Room", "Lab", "Course", "Faculty")


def _names(scheduler, category: str) -> list[str]:
    """Names of every item in ``category``, in display order."""
    if category == "Room":
        return [room.name for room in scheduler.rooms]
    if category == "Lab":
        return [lab.name for lab in scheduler.labs]
    if category == "Course":
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
    "Room": _remove_room,
    "Lab": _remove_lab,
    "Course": _remove_course,
    "Faculty": _remove_faculty,
}


def delete(console: Console, session: Session) -> None:
    """Prompt for a category and item, confirm, then remove it and every reference to it."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    config = session.config

    category_choice = ask_menu(console, "Delete what?", [*_CATEGORIES, CANCEL])
    if category_choice == len(_CATEGORIES) + 1:
        console.say(CANCELLED)
        return
    category = _CATEGORIES[category_choice - 1]

    names = _names(config.config, category)
    if not names:
        console.say(NOTHING_TO_DELETE)
        return

    item_choice = ask_menu(console, f"Delete which {category.lower()}?", [*names, CANCEL])
    if item_choice == len(names) + 1:
        console.say(CANCELLED)
        return
    name = names[item_choice - 1]

    if not ask_yes_no(console, f"Delete {category.lower()} '{name}'? (yes/no): "):
        console.say(CANCELLED)
        return

    try:
        with config.edit_mode() as working:
            _REMOVERS[category](working.config, name)
    except ValidationError as error:
        console.say(WOULD_LEAVE_INVALID.format(name=name, error=error))
        return

    console.say(DELETED.format(name=name))
