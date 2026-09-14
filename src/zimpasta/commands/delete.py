"""Delete a room, lab, course, or faculty member from the loaded configuration."""

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


def _names(config, category: str) -> list[str]:
    """Names of every item in ``category``, in display order."""
    if category == "Room":
        return [room.name for room in config.config.rooms]
    if category == "Lab":
        return [lab.name for lab in config.config.labs]
    if category == "Course":
        return [course.course_id for course in config.config.courses]
    return [faculty.name for faculty in config.config.faculty]


def _remove(config, category: str, name: str) -> None:
    """Remove the item named ``name`` from ``category`` in-place."""
    if category == "Room":
        config.config.rooms = [
            room for room in config.config.rooms if room.name != name
        ]
    elif category == "Lab":
        config.config.labs = [lab for lab in config.config.labs if lab.name != name]
    elif category == "Course":
        config.config.courses = [
            course for course in config.config.courses if course.course_id != name
        ]
    else:
        config.config.faculty = [
            faculty for faculty in config.config.faculty if faculty.name != name
        ]


def delete(console: Console, session: Session) -> None:
    """Prompt for a category and item, confirm, then remove it from ``session.config``."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    config = session.config

    category_choice = ask_menu(console, "Delete what?", [*_CATEGORIES, CANCEL])
    if category_choice == len(_CATEGORIES) + 1:
        console.say(CANCELLED)
        return
    category = _CATEGORIES[category_choice - 1]

    names = _names(config, category)
    if not names:
        console.say(NOTHING_TO_DELETE)
        return

    item_choice = ask_menu(
        console, f"Delete which {category.lower()}?", [*names, CANCEL]
    )
    if item_choice == len(names) + 1:
        console.say(CANCELLED)
        return
    name = names[item_choice - 1]

    if not ask_yes_no(console, f"Delete {category.lower()} '{name}'? (yes/no): "):
        console.say(CANCELLED)
        return

    try:
        with config.edit_mode() as working:
            _remove(working, category, name)
    except ValidationError as error:
        console.say(WOULD_LEAVE_INVALID.format(name=name, error=error))
        return

    console.say(DELETED.format(name=name))
