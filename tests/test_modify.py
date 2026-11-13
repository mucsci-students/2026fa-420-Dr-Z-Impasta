"""The modify command, pinned to what it does today.

These tests describe the current behavior, including known bugs (each marked "Bug:"), so
a refactor can show it changed nothing. When you fix one of those bugs, update its test.
"""

import json

import pytest
from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.command import CommandError, Registry, evaluate
from zimpasta.commands.modify import (
    MODIFY_SPECS,
    NO_CONFIG,
    id_key_choices,
    update_config,
    update_config_config,
    update_config_time_slot_config,
)
from zimpasta.session import Session

SERIALIZER_WARNING = "serialized value may not be as expected"
"""What pydantic warns when a modify left a value of the wrong type in the configuration."""


def run(session: Session, line: str) -> list[str]:
    """Run one modify command line; return what it printed."""
    console = ScriptedConsole()
    evaluate(console, session, line, Registry(MODIFY_SPECS))
    return console.output


def saved(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def session(config, config_file) -> Session:
    return Session(config=config, config_path=config_file)


@pytest.fixture
def with_flags(config_data, tmp_path):
    """A configuration with two optimizer flags, and the file it came from."""
    config_data["optimizer_flags"] = ["faculty_course", "pack_rooms"]
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(config_data), encoding="utf-8")
    return CombinedConfig.model_validate(config_data), path


def test_id_key_choices():
    assert id_key_choices("course") == (
        "course_id",
        ("course_id", "credits", "capacity", "room", "lab", "conflicts", "faculty"),
    )
    # A class has no ID choices, and only optimizer flags list theirs as a tuple.
    assert id_key_choices("class") == ("", ("credits", "day", "duration", "lab", "disabled"))
    assert id_key_choices("optimizer_flag") == (
        ("faculty_course", "faculty_room", "faculty_lab", "same_room", "same_lab", "pack_rooms"),
        ("null",),
    )
    assert id_key_choices("pizza") == ("", ())


# --------------------------------------------------------- from the shell: items


def test_a_faculty_number(session, config_file):
    assert run(session, 'modify faculty name "Dr. Smith" maximum_credits 6') == [
        "faculty update has succeeded."
    ]

    assert session.config.config.faculty[0].maximum_credits == 6
    assert saved(config_file) == session.config.model_dump(mode="json")


@pytest.mark.parametrize(
    ("kind", "name", "area"), [("room", "Room 101", "rooms"), ("lab", "Lab 101", "labs")]
)
def test_a_room_or_lab_capacity(session, config_file, kind, name, area):
    assert run(session, f'modify {kind} name "{name}" capacity 50') == [
        f"{kind} update has succeeded."
    ]

    assert getattr(session.config.config, area)[0].capacity == 50
    assert saved(config_file)["config"][area][0]["capacity"] == 50


def test_a_course_capacity(session, config_file):
    assert run(session, 'modify course course_id "CS 101" capacity 30') == [
        "course update has succeeded."
    ]

    assert [course.capacity for course in session.config.config.courses] == [30, 24]
    assert saved(config_file)["config"]["courses"][0]["capacity"] == 30


@pytest.mark.parametrize(
    "line",
    [
        "modify faculty name Aaron maximum_credits 5",
        'modify course course_id "CS 10" capacity 30',  # part of a name matches nothing
        # Bug: "course" passes the ID check because it is part of "course_id".
        'modify course course "CS 101" capacity 30',
    ],
)
def test_no_matching_item_changes_nothing(session, config_file, line):
    before = config_file.read_text(encoding="utf-8")
    kind = line.split()[1]

    assert run(session, line) == [f"{kind} update has not succeeded."]

    assert config_file.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (
            'modify course name "CS 101" capacity 30',
            "Unknown course ID: name. Options are course_id",
        ),
        (
            'modify course course_id "CS 101" bogus 1',
            "Unknown field: bogus. Options are ('course_id', 'credits', 'capacity', 'room', "
            "'lab', 'conflicts', 'faculty')",
        ),
        # Bug: a class can never be modified from the shell; every ID is unknown.
        (
            'modify class "credits: 3, M" null MON "duration: 40"',
            "Unknown class ID: credits: 3, M. Options are ",
        ),
    ],
)
def test_unknown_ids_and_fields(session, config_file, line, message):
    before = config_file.read_text(encoding="utf-8")

    with pytest.raises(CommandError) as raised:
        run(session, line)

    assert str(raised.value) == message
    assert config_file.read_text(encoding="utf-8") == before


def test_faculty_times(session, config_file):
    # Bug: the day's list of time ranges is replaced by a single string.
    with pytest.warns(UserWarning, match=SERIALIZER_WARNING):
        output = run(session, 'modify faculty name "Dr. Jones" times "MON: 10:00-12:00"')

    assert output == ["faculty update has succeeded."]
    assert session.config.config.faculty[1].times["MON"] == "10:00-12:00"
    assert saved(config_file)["config"]["faculty"][1]["times"]["MON"] == "10:00-12:00"


def test_an_existing_faculty_preference(config_data, tmp_path):
    config_data["config"]["faculty"][0]["course_preferences"] = {"CS 101": 3}
    path = tmp_path / "prefs.json"
    path.write_text(json.dumps(config_data), encoding="utf-8")
    config = CombinedConfig.model_validate(config_data)
    session = Session(config=config, config_path=path)

    assert run(session, 'modify faculty name "Dr. Smith" course_preferences "CS 101:5"') == [
        "faculty update has succeeded."
    ]

    assert config.config.faculty[0].course_preferences == {"CS 101": 5}
    assert saved(path)["config"]["faculty"][0]["course_preferences"] == {"CS 101": 5}


@pytest.mark.parametrize(
    ("line", "error"),
    [
        # Bug: a preference the faculty member doesn't have yet crashes.
        ('modify faculty name "Dr. Smith" course_preferences "CS 101:5"', KeyError),
        # Bug: a value of the wrong type crashes.
        ('modify room name "Room 101" capacity lots', ValueError),
    ],
)
def test_crashes(session, config_file, line, error):
    before = config_file.read_text(encoding="utf-8")

    with pytest.raises(error):
        run(session, line)

    assert config_file.read_text(encoding="utf-8") == before


# ---------------------------------------------- from the shell: everything else


def test_a_time_block(session, config_file):
    assert run(session, 'modify time_slot times "THU: start: 08:00" spacing 90') == [
        "time_slot update has succeeded."
    ]

    assert session.config.time_slot_config.times["THU"][0].spacing == 90
    assert saved(config_file)["time_slot_config"]["times"]["THU"][0]["spacing"] == 90


def test_an_optimizer_flag(session, config_file):
    before = config_file.read_text(encoding="utf-8")

    # Bug: "null", which the flag syntax needs, counts as a missing value.
    assert run(session, "modify optimizer_flag faculty_course null null") == [
        "\nPlease specify a ",
        "- value: ",
        "\n",
    ]
    assert config_file.read_text(encoding="utf-8") == before


def test_missing_fields_are_listed(session):
    assert run(session, "modify room") == [
        "\nPlease specify a ",
        "- id: ",
        "- field: ",
        "- key: ",
        "- value: ",
        "\n",
    ]


def test_without_a_configuration(config_file):
    session = Session(config=None, config_path=config_file)

    assert run(session, "modify") == [NO_CONFIG]
    assert run(session, 'modify room name "Room 101" capacity 50') == [
        "room update has not succeeded."
    ]
    assert run(session, 'modify time_slot times "THU: start: 08:00" spacing 90') == [
        "time_slot update has not succeeded."
    ]


# ------------------------------------------------- the update functions directly


def test_the_first_optimizer_flag(with_flags):
    config, path = with_flags

    with pytest.warns(UserWarning, match=SERIALIZER_WARNING):
        update_config("optimizer_flag", "faculty_course", "x", "null", "null", config, path)

    # Bug: the flag is replaced by the value, without validation.
    assert config.optimizer_flags == ["null", "pack_rooms"]
    assert saved(path)["optimizer_flags"] == ["null", "pack_rooms"]


def test_a_later_optimizer_flag(with_flags):
    config, path = with_flags
    path.write_text("", encoding="utf-8")

    update_config("optimizer_flag", "pack_rooms", "x", "null", "null", config, path)

    # Bug: only the first flag is checked, but the file is still rewritten.
    assert config.optimizer_flags == ["faculty_course", "pack_rooms"]
    assert saved(path) == config.model_dump(mode="json")


def test_no_optimizer_flags(config, config_file):
    before = config_file.read_text(encoding="utf-8")

    update_config("optimizer_flag", "faculty_course", "x", "null", "null", config, config_file)

    assert config.optimizer_flags == []
    assert config_file.read_text(encoding="utf-8") == before


def test_a_time_block_that_does_not_exist(config, config_file):
    config_file.write_text("", encoding="utf-8")

    update_config("time_slot", "times", "THU: start: 09:00", "spacing", "90", config, config_file)

    # Bug: nothing matched, but the file is still rewritten.
    assert config.time_slot_config.times["THU"][0].spacing == 60
    assert saved(config_file) == config.model_dump(mode="json")


@pytest.mark.parametrize("pattern", ["credits: 3, MW", "credits: 4, MW, lab: WED"])
def test_class_patterns(config, config_file, pattern):
    original = config.model_dump(mode="json")
    config_file.write_text("", encoding="utf-8")

    update_config_time_slot_config(
        "class", pattern, "null", "MON", "duration: 40", config, config_file
    )

    # Bug: only the first pattern is checked, and nothing changes, but the file is rewritten.
    assert config.model_dump(mode="json") == original
    assert saved(config_file) == original


def test_a_four_credit_lab_pattern(config_data, tmp_path):
    lab_pattern = {
        "credits": 4,
        "meetings": [
            {"day": "MON", "duration": 75, "lab": False},
            {"day": "WED", "duration": 110, "lab": True},
        ],
    }
    config_data["time_slot_config"]["classes"].insert(0, lab_pattern)
    config = CombinedConfig.model_validate(config_data)
    original = config.model_dump(mode="json")
    path = tmp_path / "lab.json"

    update_config_time_slot_config(
        "class", "credits: 4, MW, lab: WED", "null", "WED", "duration: 100", config, path
    )

    # Bug: the lab day keeps its leading space (" WED"), so no meeting ever matches.
    assert config.model_dump(mode="json") == original
    assert saved(path) == original


def test_a_class_pattern_that_crashes(config, config_file):
    before = config_file.read_text(encoding="utf-8")

    # Bug: matching the first pattern's meeting count crashes.
    with pytest.raises(AttributeError):
        update_config_time_slot_config(
            "class", "credits: 3, M", "null", "MON", "duration: 40", config, config_file
        )

    assert config_file.read_text(encoding="utf-8") == before


def test_without_a_path(config, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    update_config_config("room", "name", "Room 101", "capacity", "50", config, None)

    # Bug: with no path, the configuration is written to a file named "None".
    assert saved(tmp_path / "None")["config"]["rooms"][0]["capacity"] == 50


def test_what_the_update_functions_return(config, config_file, with_flags):
    flags_config, flags_path = with_flags
    room = ("room", "name", "Room 101", "capacity", "50")
    flag = ("optimizer_flag", "faculty_course", "x", "null", "null")
    pattern = ("class", "credits: 3, MW", "null", "MON", "duration: 40")

    assert update_config_config(*room, config, config_file) is True
    assert (
        update_config_config(
            "faculty", "name", "Aaron", "maximum_credits", "5", config, config_file
        )
        is False
    )
    assert update_config_config(*room, None, config_file) is False

    time_block = ("time_slot", "times", "THU: start: 08:00", "spacing", "90")
    assert update_config(*time_block, config, config_file) is True
    assert update_config(*flag, config, config_file) is False  # the fixture has no flags
    # Bug: True for a flag that isn't first, though nothing changed.
    assert (
        update_config("optimizer_flag", "pack_rooms", "x", "null", "null", flags_config, flags_path)
        is True
    )
    assert update_config(*flag, None, config_file) is False

    assert update_config_time_slot_config(*pattern, config, config_file) is True
    assert update_config_time_slot_config(*pattern, None, config_file) is False
