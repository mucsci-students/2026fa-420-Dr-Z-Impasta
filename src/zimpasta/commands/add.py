"""Add a room, lab, course, or faculty member to the loaded configuration.

``add room "Room 102" --capacity 30`` runs straight away; a bare ``add``, or one
missing a required field, prompts for what's missing and then runs the same
command through the evaluator -- mirroring delete.py's build()/handler split.

A course id is not required to be unique: a configuration lists the same course_id
once per section (see delete.py's docstring and the CMSC 161 sections in
tests/test_delete.py). So adding a course never checks for a duplicate course_id;
that would block adding a second section. Every other rule, such as duplicate
room, lab, or faculty names, is left to CombinedConfig's own validation, and its
pydantic.ValidationError is reported, the same way delete.py reports removals that
would leave the configuration invalid.

The library rejects a course with faculty=None unless some faculty member's
course_preferences already names that course_id (a new course_id never is), and a
course with room=[] (no class pattern can run without a room). So `add course`
requires both --faculty and --room (comma-separated for more than one) and always
passes real lists.

Faculty times and preferences start empty, and rooms and labs get no features or
times, since add only collects scalar fields; fill them in afterwards with modify.
"""

from collections.abc import Callable

from pydantic import ValidationError
from scheduler import CourseConfig, FacultyConfig, LabConfig, RoomConfig

from zimpasta.command import CommandSpec, Invocation, Option, Positional
from zimpasta.commands.common import KINDS
from zimpasta.commands.common import NO_CONFIG_TO_EDIT as NO_CONFIG
from zimpasta.console import Console
from zimpasta.prompts import ask_choice, ask_int
from zimpasta.session import Session

ADDED = "Added {name}."
CANCELLED = "Cancelled. Nothing was added."
INVALID = "Can't add {name}: {error}"

# The scalar fields each kind needs beyond its id, matching sample_config.json.
# List/dict fields (course room/lab/conflicts; faculty times/*_preferences)
# are still not collected here -- Positional/Option only carries scalar strings.
# They default empty/None and are meant to be filled in afterward via 'modify'.
REQUIRED_INT_FIELDS: dict[str, tuple[str, ...]] = {
    "room": ("capacity",),
    "lab": ("capacity",),
    "course": ("credits", "capacity"),
    "faculty": ("maximum-credits", "minimum-credits", "unique-course-limit"),
}

# Both are required for a course even though neither is a number (see the module
# docstring for why the library needs them).
REQUIRED_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "course": ("faculty", "room"),
}

EMPTY_TIMES = {"MON": [], "TUE": [], "WED": [], "THU": [], "FRI": []}

NewEntry = Callable[[str, dict[str, int], dict[str, list[str]]], object]
"""Builds a new entry from its id, its whole-number fields, and its list fields."""

NEW_ENTRIES: dict[str, tuple[str, NewEntry]] = {
    "room": (
        "rooms",
        lambda item_id, fields, lists: RoomConfig(name=item_id, capacity=fields["capacity"]),
    ),
    "lab": (
        "labs",
        lambda item_id, fields, lists: LabConfig(name=item_id, capacity=fields["capacity"]),
    ),
    # No duplicate check: a repeated course_id is another section of the same course.
    # Faculty and room can't be empty, or the library rejects the course.
    "course": (
        "courses",
        lambda item_id, fields, lists: CourseConfig(
            course_id=item_id,
            credits=fields["credits"],
            capacity=fields["capacity"],
            room=lists["room"],
            lab=[],
            conflicts=[],
            faculty=lists["faculty"],
        ),
    ),
    # Times and preferences start empty; fill them in afterwards with modify.
    "faculty": (
        "faculty",
        lambda item_id, fields, lists: FacultyConfig(
            name=item_id,
            maximum_credits=fields["maximum-credits"],
            minimum_credits=fields["minimum-credits"],
            unique_course_limit=fields["unique-course-limit"],
            times=dict(EMPTY_TIMES),
            course_preferences={},
            room_preferences={},
            lab_preferences={},
        ),
    ),
}
"""For each kind: the list on ``config.config`` it goes in, and how to build one."""


def _label(kind: str, field: str) -> str:
    # Just turns something like ("faculty", "maximum-credits") into a readable
    # prompt like "Faculty maximum credits" -- swap the dash for a space and
    # capitalize the kind so it reads like a normal sentence instead of a flag name.
    return f"{kind.capitalize()} {field.replace('-', ' ')}"


# This is the "interactive mode" for add -- it only runs when the person
# typed something incomplete, like just "add" or "add room". Its whole job
# is to fill in whatever's missing and hand back a complete Invocation so
# evaluate() can run it through add() the normal way. Mirrors how
# delete.py's build() is structured, so the two commands feel consistent.
def build(console: Console, session: Session, invocation: Invocation) -> Invocation | None:

    if session.config is None:
        console.say(
            NO_CONFIG
        )  # Can't ask the user anything useful if there's nothing loaded to add to.
        return None

    positionals = dict(invocation.positionals)
    options = dict(invocation.options)

    # if you can't ask "capacity?" before you know if it's a room or a course).
    if "kind" not in positionals:
        positionals["kind"] = ask_choice(console, "Add what? ", KINDS)
    kind = positionals["kind"]

    if "id" not in positionals:
        item_id = console.ask(f"{kind.capitalize()} id: ").strip()
        if not item_id:
            # Treat a blank id as "changed my mind" rather than looping forever
            # asking again easier to just bail out and let them retype "add".
            console.say(CANCELLED)
            return None
        positionals["id"] = item_id

    # Ask for whatever numeric fields this particular kind needs
    # (rooms/labs just need capacity, courses need credits + capacity, faculty
    # need three different limits).
    for field in REQUIRED_INT_FIELDS.get(kind, ()):
        if field not in options:
            options[field] = str(ask_int(console, f"{_label(kind, field)}: ", minimum=0))

    # Same idea, but for the list-shaped fields (currently just faculty/room on
    # a course). We keep asking until they actually type something, since an
    # empty answer here would just fail validation later anyway -- better to
    # catch it now while we're already talking to them.
    for field in REQUIRED_LIST_FIELDS.get(kind, ()):
        if field not in options:
            while True:
                raw = console.ask(f"{_label(kind, field)} (comma-separated, at least one): ")
                if raw.strip():
                    options[field] = raw
                    break
                console.say("At least one name is required.")

    return invocation.with_values(positionals=positionals, options=options)


# Pulls one --option value out and turns it into a real int, or blows up
# with a message that's actually useful to read. We use this on both the
# "typed a full one-liner" path and the "went through the builder" path,
# so whichever way the value got in, it gets checked the same way here.
def _required_int(invocation: Invocation, kind: str, field: str) -> int:

    raw = invocation.get(field)
    if raw is None:
        # This is the case where someone typed e.g. "add room R1" and just
        # forgot to include capacity so, We don't try to guess a default.
        raise ValueError(f"--{field} is required for {kind}.")
    try:
        return int(str(raw))
    except ValueError:
        # They gave us something, just not a number -- e.g. --capacity lots.
        raise ValueError(f"--{field} must be a whole number.") from None


# Same idea as _required_int above, but for the comma-separated fields
# (right now just faculty/room on a course). We split on commas and throw
# away anything blank, so "Dr. Smith, , Dr. Jones" doesn't sneak an empty
# name into the list.
def _required_list(invocation: Invocation, kind: str, field: str) -> list[str]:

    raw = invocation.get(field)
    if raw is None or not str(raw).strip():
        raise ValueError(f"--{field} is required for {kind} (comma-separate multiple names).")
    return [item.strip() for item in str(raw).split(",") if item.strip()]


# This is the actual "do the thing" function -- by the time we're here,
# evaluate() has already guaranteed kind and id are present (that's what
# "complete" means to the framework). Everything else we still have to
# check ourselves, since --capacity/--faculty/etc. aren't marked required
# at the framework level (they can't be, since which ones are required
# depends on the kind, and the framework doesn't know about kinds).
def add(console: Console, session: Session, invocation: Invocation) -> None:

    if session.config is None:
        console.say(NO_CONFIG)
        return

    kind = str(invocation.get("kind"))
    item_id = str(invocation.get("id"))

    try:
        # Grab and validate every number this kind needs (capacity, credits,
        # whatever) plus every list this kind needs (currently just courses'
        # faculty/room). If anything's missing or malformed we bail out here
        # with a message, before we ever touch the actual configuration.
        fields = {
            field: _required_int(invocation, kind, field)
            for field in REQUIRED_INT_FIELDS.get(kind, ())
        }
        list_fields = {
            field: _required_list(invocation, kind, field)
            for field in REQUIRED_LIST_FIELDS.get(kind, ())
        }
    except ValueError as exc:
        console.say(str(exc))
        return

    items, new_entry = NEW_ENTRIES[kind]
    try:
        # edit_mode() makes the edit atomic and validated. The library re-validates only on
        # assignment, not on mutation, so the list is reassigned whole rather than appended to.
        with session.config.edit_mode() as working:
            scheduler = working.config
            entries = getattr(scheduler, items)
            setattr(scheduler, items, [*entries, new_entry(item_id, fields, list_fields)])
    except ValidationError as exc:
        # Whatever the library didn't like about this addition -- a duplicate
        # name, some cross-reference that doesn't hold up, etc. -- gets
        # reported here rather than us trying to guess every rule ourselves.
        console.say(INVALID.format(name=item_id, error=exc))
        return

    console.say(ADDED.format(name=item_id))


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "add",
        positionals=(Positional("kind", choices=KINDS), Positional("id")),
        options=(
            Option("capacity", help="seating/room capacity (room, lab, course)"),
            Option("credits", help="credit hours (course)"),
            Option(
                "faculty",
                help="comma-separated faculty name(s) teaching this course (required)",
            ),
            Option(
                "room",
                help="comma-separated room name(s) this course can meet in (required)",
            ),
            Option("maximum-credits", help="maximum credits assignable (faculty)"),
            Option("minimum-credits", help="minimum credits assignable (faculty)"),
            Option("unique-course-limit", help="distinct courses this faculty may teach"),
        ),
        description="Add a course, room, lab, or faculty member",
        handler=add,
        builder=build,
    ),
)
