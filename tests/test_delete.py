from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.commands.delete import (
    CANCELLED,
    DELETED,
    NO_CONFIG,
    NOTHING_TO_DELETE,
    delete,
)
from zimpasta.session import Session


def test_deletes_the_chosen_item(config: CombinedConfig):
    console = ScriptedConsole(["3", "2", "yes"])  # Course -> CS 102 -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="CS 102") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101"]


def test_cancel_at_category_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["5"])  # Cancel

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_cancel_at_item_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["1", "2"])  # Room -> Cancel

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [r.name for r in config.config.rooms] == ["Room 101"]


def test_declining_confirmation_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["3", "1", "no"])  # Course -> CS 101 -> decline

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_no_config_loaded_reports_and_asks_nothing():
    console = ScriptedConsole([])

    delete(console, Session(config=None))

    assert console.output == [NO_CONFIG]


def test_delete_that_would_leave_config_invalid_is_rolled_back(config: CombinedConfig):
    # Dr. Smith teaches CS 101; removing her breaks CS 101's faculty reference.
    console = ScriptedConsole(["4", "1", "yes"])  # Faculty -> Dr. Smith -> confirm

    delete(console, Session(config=config))

    assert "Can't delete Dr. Smith" in console.output[-1]
    assert [f.name for f in config.config.faculty] == ["Dr. Smith", "Dr. Jones"]


def test_nothing_to_delete_reports_without_further_prompts(config_data: dict):
    config_data["config"]["labs"] = []
    for course in config_data["config"]["courses"]:
        course["lab"] = []
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["2"])  # Lab

    delete(console, Session(config=config))

    assert console.output[-1] == NOTHING_TO_DELETE


def test_deleting_a_room_strips_it_from_courses_and_preferences(config_data: dict):
    config_data["config"]["rooms"].append({"name": "Room 102", "capacity": 30})
    config_data["config"]["courses"][0]["room"] = ["Room 101", "Room 102"]
    config_data["config"]["faculty"][0]["room_preferences"] = {"Room 102": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["1", "2", "yes"])  # Room -> Room 102 -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="Room 102") in console.output
    assert [room.name for room in config.config.rooms] == ["Room 101"]
    assert config.config.courses[0].room == ["Room 101"]
    assert config.config.faculty[0].room_preferences == {}


def test_deleting_a_lab_strips_it_from_courses_and_preferences(config_data: dict):
    config_data["config"]["faculty"][0]["lab_preferences"] = {"Lab 101": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["2", "1", "yes"])  # Lab -> Lab 101 -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="Lab 101") in console.output
    assert config.config.labs == []
    assert all(course.lab == [] for course in config.config.courses)
    assert config.config.faculty[0].lab_preferences == {}


def test_deleting_a_course_strips_it_from_conflicts_and_preferences(config_data: dict):
    config_data["config"]["faculty"][0]["course_preferences"] = {"CS 101": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["3", "1", "yes"])  # Course -> CS 101 -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="CS 101") in console.output
    assert [course.course_id for course in config.config.courses] == ["CS 102"]
    assert config.config.courses[0].conflicts == []
    assert config.config.faculty[0].course_preferences == {}


def test_deleting_a_faculty_member_strips_them_from_courses(config_data: dict):
    config_data["config"]["courses"][0]["faculty"] = ["Dr. Smith", "Dr. Jones"]
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["4", "2", "yes"])  # Faculty -> Dr. Jones -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="Dr. Jones") in console.output
    assert [faculty.name for faculty in config.config.faculty] == ["Dr. Smith"]
    assert [course.faculty for course in config.config.courses] == [
        ["Dr. Smith"],
        ["Dr. Smith"],
    ]


def test_deleting_the_only_room_is_refused(config: CombinedConfig):
    console = ScriptedConsole(["1", "1", "yes"])  # Room -> Room 101 -> confirm

    delete(console, Session(config=config))

    assert "Can't delete Room 101" in console.output[-1]
    assert [room.name for room in config.config.rooms] == ["Room 101"]
    assert config.config.courses[0].room == ["Room 101"]
