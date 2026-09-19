"""Tests for zimpasta/commands/add.py, in the same style as delete_test.py:
full command lines, the bare-verb builder path, and the no-config case, checked
against the real CombinedConfig (via the shared `config`/`config_data` fixtures)
rather than a hand-rolled fake.

ASSUMES your project's tests/conftest.py already provides `config` and
`config_data` fixtures (the same ones delete_test.py uses) with a room named
"Room 101", courses "CS 101"/"CS 102", and faculty "Dr. Smith"/"Dr. Jones" --
inferred from delete_test.py's own assertions, not confirmed against your real
fixtures. If your actual fixture data differs, the exact names/counts below may
need adjusting, but the shape of each test should still hold.

Also assumes ADDED/CANCELLED/INVALID/NO_CONFIG are exported from add.py as
message-format constants, mirroring delete.py's DELETED/CANCELLED/
WOULD_LEAVE_INVALID/NO_CONFIG.
"""

from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.command import Registry, evaluate
from zimpasta.commands.add import ADDED, CANCELLED, NO_CONFIG, SPECS
from zimpasta.session import Session

REGISTRY = Registry(SPECS)


def run(console: ScriptedConsole, session: Session, line: str) -> None:
    # Small helper so every test below can just say run(console, session, "add ...")
    # instead of repeating evaluate(..., REGISTRY) everywhere. Keeps the actual
    # test bodies focused on what's being checked, not the plumbing.
    evaluate(console, session, line, REGISTRY)


# Basic case: type a complete "add room" line and check the room shows up.
def test_full_command_line_adds_a_room(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add room "Room 102" --capacity 30')

    assert ADDED.format(name="Room 102") in console.output
    assert [r.name for r in config.config.rooms] == ["Room 101", "Room 102"]


# Same idea as the room test above, just for labs instead.
def test_full_command_line_adds_a_lab(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add lab "Lab 102" --capacity 20')

    assert ADDED.format(name="Lab 102") in console.output
    assert [lab.name for lab in config.config.labs] == ["Lab 101", "Lab 102"]


# Courses need more than just a capacity -- credits, plus the faculty/room
# fields we only found out were required after the real library rejected an
# empty faculty/room list. This confirms all four together actually work.
def test_full_command_line_adds_a_course(config: CombinedConfig):
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add course "CS 103" --credits 3 --capacity 30 --faculty "Dr. Smith" --room "Room 101"',
    )

    assert ADDED.format(name="CS 103") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102", "CS 103"]


def test_course_faculty_option_is_required(config: CombinedConfig):
    """CONFIRMED real validation rule: a course with faculty=None needs an
    existing preference to derive from, which a brand-new course never has."""
    # Leave --faculty off entirely and make sure we get a clear error instead
    # of either crashing or silently creating a broken course.
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add course "CS 103" --credits 3 --capacity 30 --room "Room 101"',
    )

    assert console.output[-1] == (
        "--faculty is required for course (comma-separate multiple names)."
    )
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_course_room_option_is_required(config: CombinedConfig):
    """CONFIRMED real validation rule: a course with room=[] has no enabled
    class pattern that can run without a room."""
    # Mirror of the faculty test above, but for --room this time.
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add course "CS 103" --credits 3 --capacity 30 --faculty "Dr. Smith"',
    )

    assert console.output[-1] == ("--room is required for course (comma-separate multiple names).")
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


# Make sure a course can actually have more than one faculty member attached --
# not just the single-name case every other test uses.
def test_course_faculty_option_accepts_multiple_comma_separated_names(config: CombinedConfig):
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add course "CS 103" --credits 3 --capacity 30 --faculty '
        '"Dr. Smith, Dr. Jones" --room "Room 101"',
    )

    assert ADDED.format(name="CS 103") in console.output
    added = config.config.courses[-1]
    assert added.faculty == ["Dr. Smith", "Dr. Jones"]


# Same shape as the room/lab tests, but for faculty -- checks all three of the
# limit fields (max/min credits, unique course limit) land correctly.
def test_full_command_line_adds_faculty(config: CombinedConfig):
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add faculty "Dr. Lee" --maximum-credits 12 --minimum-credits 12 --unique-course-limit 2',
    )

    assert ADDED.format(name="Dr. Lee") in console.output
    assert [f.name for f in config.config.faculty] == ["Dr. Smith", "Dr. Jones", "Dr. Lee"]


# The most "bare" case possible: just type "add" and nothing else, and make
# sure it walks you through kind, then id, then capacity, one at a time.
def test_bare_verb_asks_kind_id_and_capacity(config: CombinedConfig):
    console = ScriptedConsole(["room", "Room 102", "30"])  # kind -> id -> capacity

    run(console, Session(config=config), "add")

    assert "Running: add room 'Room 102' --capacity 30" in console.output
    assert ADDED.format(name="Room 102") in console.output
    assert [r.name for r in config.config.rooms] == ["Room 101", "Room 102"]


# Half-typed command: "add room" already tells it the kind, so it should only
# ask for the two things still missing (id, capacity) and not re-ask for kind.
def test_kind_given_asks_only_the_remaining_fields(config: CombinedConfig):
    console = ScriptedConsole(["Room 102", "30"])  # id -> capacity (kind already given)

    run(console, Session(config=config), "add room")

    assert ADDED.format(name="Room 102") in console.output
    assert [r.name for r in config.config.rooms] == ["Room 101", "Room 102"]


def test_kind_and_id_given_asks_only_for_capacity(config: CombinedConfig):
    """NOTE: evaluate() only calls the builder when a Positional (kind/id) is
    missing -- with both already given, an invocation is 'complete' regardless
    of --capacity, so evaluate() would call the handler directly and fail (see
    test_missing_required_option_reports_and_adds_nothing). To exercise the
    builder's own field-filling logic here, call build() directly instead."""
    # This one's a bit different from the others above: we can't get here
    # through a normal "add room X" line (see the note), so we call the
    # builder function directly to check its own prompting logic in isolation.
    from zimpasta.commands.add import SPECS as _SPECS

    console = ScriptedConsole(["30"])  # capacity only
    invocation = _SPECS[0].parse(["room", "Room 102"])

    built = _SPECS[0].builder(console, Session(config=config), invocation)

    assert built.get("capacity") == "30"


# Courses have the most fields to prompt for -- this checks the builder asks
# for them in a sensible, consistent order (credits, capacity, faculty, room)
# rather than jumping around.
def test_course_prompts_for_credits_then_capacity_then_faculty_then_room(config: CombinedConfig):
    from zimpasta.commands.add import SPECS as _SPECS

    console = ScriptedConsole(["3", "30", "Dr. Smith", "Room 101"])
    invocation = _SPECS[0].parse(["course", "CS 103"])

    built = _SPECS[0].builder(console, Session(config=config), invocation)

    assert (
        built.get("credits"),
        built.get("capacity"),
        built.get("faculty"),
        built.get("room"),
    ) == ("3", "30", "Dr. Smith", "Room 101")


# Faculty have three required numbers -- check they're asked for in the same
# order they're declared in REQUIRED_INT_FIELDS.
def test_faculty_prompts_for_all_three_limits_in_order(config: CombinedConfig):
    from zimpasta.commands.add import SPECS as _SPECS

    console = ScriptedConsole(["12", "12", "2"])  # max -> min -> unique-course-limit
    invocation = _SPECS[0].parse(["faculty", "Dr. Lee"])

    built = _SPECS[0].builder(console, Session(config=config), invocation)

    assert (
        built.get("maximum-credits"),
        built.get("minimum-credits"),
        built.get("unique-course-limit"),
    ) == ("12", "12", "2")


# If someone starts adding something and then just hits enter (blank id), we
# should treat that as "never mind" and add nothing, not keep pestering them.
def test_empty_id_during_builder_cancels_without_adding(config: CombinedConfig):
    console = ScriptedConsole(["room", "   "])  # kind, then a blank id

    run(console, Session(config=config), "add")

    assert console.output[-1] == CANCELLED
    assert [r.name for r in config.config.rooms] == ["Room 101"]


# Whether you type a full line or just "add" with nothing loaded, you should
# get the same clear "load something first" message and nothing else happens.
def test_no_config_loaded_reports_and_asks_nothing():
    console = ScriptedConsole([])

    run(console, Session(config=None), 'add room "Room 102" --capacity 30')
    run(console, Session(config=None), "add")

    assert console.output == [NO_CONFIG, NO_CONFIG]


# =============================================================================
# Validation and error paths
# =============================================================================


# A one-liner that's missing --capacity entirely (not just given a bad value)
# should fail with a clear message instead of crashing.
def test_missing_required_option_reports_and_adds_nothing(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add room "Room 102"')

    assert console.output[-1] == "--capacity is required for room."
    assert [r.name for r in config.config.rooms] == ["Room 101"]


# Same as above, but this time --capacity IS given, just not a number.
def test_non_numeric_capacity_reports_and_adds_nothing(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add room "Room 102" --capacity lots')

    assert console.output[-1] == "--capacity must be a whole number."
    assert [r.name for r in config.config.rooms] == ["Room 101"]


# Trying to add a room that already exists should be rejected by the library
# and reported back to the user, not silently overwrite/duplicate anything.
def test_duplicate_room_name_is_reported_and_not_added(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add room "Room 101" --capacity 30')

    assert console.output[-1].startswith("Can't add Room 101:")
    assert len(config.config.rooms) == 1


# Same duplicate check as above, just for labs.
def test_duplicate_lab_name_is_reported_and_not_added(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), 'add lab "Lab 101" --capacity 20')

    assert console.output[-1].startswith("Can't add Lab 101:")
    assert len(config.config.labs) == 1


# Same duplicate check again, this time for faculty.
def test_duplicate_faculty_name_is_reported_and_not_added(config: CombinedConfig):
    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add faculty "Dr. Smith" --maximum-credits 12 --minimum-credits 12 --unique-course-limit 2',
    )

    assert console.output[-1].startswith("Can't add Dr. Smith:")
    assert len(config.config.faculty) == 2


# Unlike rooms/labs/faculty above, adding "CS 101" again should NOT be
# treated as a duplicate -- it's just another section of the same course,
# so we expect it to succeed and show up as a second entry in the list.


def test_repeating_a_course_id_adds_a_new_section_instead_of_erroring(config: CombinedConfig):
    """Mirrors delete_test.py's own CMSC 161 x3 example: a course_id may
    legitimately appear more than once, as separate sections."""

    console = ScriptedConsole([])

    run(
        console,
        Session(config=config),
        'add course "CS 101" --credits 3 --capacity 30 --faculty "Dr. Smith" --room "Room 101"',
    )

    assert ADDED.format(name="CS 101") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102", "CS 101"]
