"""Add a room, lab, course, or faculty member to the loaded configuration.

``add room "Room 102" --capacity 30`` runs straight away; a bare ``add``, or one
missing a required field, prompts for what's missing and then runs the same
command through the evaluator -- mirroring delete.py's build()/handler split.

A course id is NOT required to be unique: the real configuration may legitimately
list the same course_id more than once, once per section (see delete.py's own
docstring and delete_test.py's CMSC 161 x3 example). So adding a course never
checks for a duplicate course_id itself -- that would incorrectly block adding a
second section of an existing course. Room/lab/faculty uniqueness, if the library
enforces it at all, is left entirely to CombinedConfig's own validation; we only
catch and report whatever pydantic.ValidationError it raises, the same way
delete.py catches ValidationError from removals that would leave things invalid.

CONFIRMED by real validation failures while testing this file:
  - A course with faculty=None is only valid if some existing faculty member's
    course_preferences already names that course_id -- which a brand-new
    course_id never has yet.
  - A course with room=[] has "no enabled class pattern that can run without
    a room" -- every course needs at least one room.
So `add course` requires both --faculty and --room (each comma-separated for
more than one), and always passes real lists instead of None/[].

UNCONFIRMED / TODO, pending full confirmation from scheduler.py:
  - RoomConfig is CONFIRMED as the real class (seen directly in a pytest
    traceback: RoomConfig(name='Room 101', capacity=40, features=set(),
    times=None) -- note it also has `features` and `times` fields we don't
    set, apparently optional with defaults).
  - LabConfig/CourseConfig/FacultyConfig are assumed to follow the same
    *Config naming pattern as RoomConfig, but are NOT yet confirmed the same
    way. Run `python3 -c "import scheduler; print(dir(scheduler))"` to check.
  - Faculty's `times`/`*_preferences` fields are given empty defaults here
    since add only collects scalar fields (see the module-level note below on
    that same limitation from the earlier version of this file).
  - Whether CombinedConfig actually rejects a duplicate room/lab/faculty name
    is unconfirmed -- we don't pre-check it ourselves, only report if it raises.
"""

from pydantic import ValidationError

from zimpasta.command import CommandSpec, Invocation, Option, Positional
from zimpasta.console import Console
from zimpasta.prompts import ask_choice, ask_int
from zimpasta.session import Session

KINDS: tuple[str, ...] = ("course", "room", "lab", "faculty")
"""Categories, in the same order delete.py's KINDS lists them."""

NO_CONFIG = "No configuration loaded. Load one first."
"""Matches delete.py's NO_CONFIG wording exactly, for consistency across commands."""

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

# CONFIRMED by real validation failures (not guesses): a course with
# faculty=None needs an existing preference to derive from (which a brand-new
# course never has), and a course with room=[] has "no enabled class pattern
# that can run without a room". So both --faculty and --room are effectively
# required when adding a course, even though neither is an "int" field.
REQUIRED_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "course": ("faculty", "room"),
}

_EMPTY_TIMES = {"MON": [], "TUE": [], "WED": [], "THU": [], "FRI": []}


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
            # Treat a blank id as "changed my mind" rather than looping forever asking again easier to just bail out and let them retype "add".
            console.say(CANCELLED)
            return None
        positionals["id"] = item_id

    # Ask for whatever numeric fields this particular kind needs (rooms/labs just need capacity, courses need credits + capacity, faculty need three different limits).
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

    # CONFIRMED from your traceback: the real class is RoomConfig, not Room --
    # `Room`/`Lab`/`Course`/`Faculty` in scheduler are type aliases (not
    # callable), which is exactly the TypeError you hit. LabConfig/CourseConfig/
    # FacultyConfig follow the same *Config naming pattern seen on RoomConfig,
    # but are NOT yet confirmed the same way -- verify with the two commands
    # from my last message and tell me if any of these three are wrong.
    from scheduler import CourseConfig, FacultyConfig, LabConfig, RoomConfig

    try:
        # edit_mode() is the library's way of doing an atomic, validated edit --
        # we build the new list (old items plus the one we're adding) and
        # reassign it as a whole, rather than appending in place. That matters
        # because the library only re-validates on assignment, not on mutation,
        # so scheduler.rooms.append(...) would silently skip validation.
        with session.config.edit_mode() as working:
            scheduler = working.config
            if kind == "room":
                scheduler.rooms = [
                    *scheduler.rooms,
                    RoomConfig(name=item_id, capacity=fields["capacity"]),
                ]
            elif kind == "lab":
                scheduler.labs = [
                    *scheduler.labs,
                    LabConfig(name=item_id, capacity=fields["capacity"]),
                ]
            elif kind == "course":
                # No duplicate check here on purpose -- a repeated course_id is
                # a new section (same course, different offering), not a
                # mistake. See the module docstring for the CMSC 161 example
                # that proves this. Also: faculty and room can't be left empty
                # for a course, or the library's own validation rejects it, so
                # both come from list_fields rather than defaulting to None/[].
                scheduler.courses = [
                    *scheduler.courses,
                    CourseConfig(
                        course_id=item_id,
                        credits=fields["credits"],
                        capacity=fields["capacity"],
                        room=list_fields["room"],
                        lab=[],
                        conflicts=[],
                        faculty=list_fields["faculty"],
                    ),
                ]
            elif kind == "faculty":
                # Faculty don't have the same "can't be empty" problem courses
                # do, so we're fine defaulting their preferences/times to
                # nothing for now -- someone can fill those in later via modify.
                scheduler.faculty = [
                    *scheduler.faculty,
                    FacultyConfig(
                        name=item_id,
                        maximum_credits=fields["maximum-credits"],
                        minimum_credits=fields["minimum-credits"],
                        unique_course_limit=fields["unique-course-limit"],
                        times=dict(_EMPTY_TIMES),
                        course_preferences={},
                        room_preferences={},
                        lab_preferences={},
                    ),
                ]
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
