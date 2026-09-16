import pytest
from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.command import CommandError, Registry, evaluate
from zimpasta.commands.delete import (
    AMBIGUOUS,
    BAD_SECTION,
    CANCELLED,
    DELETED,
    NO_CONFIG,
    NOT_FOUND,
    NOTHING_TO_DELETE,
    SPECS,
)
from zimpasta.session import Session

REGISTRY = Registry(SPECS)


def run(console: ScriptedConsole, session: Session, line: str) -> None:
    evaluate(console, session, line, REGISTRY)


def test_full_command_line_deletes_the_named_item(config: CombinedConfig):
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete course "CS 102"')

    assert DELETED.format(name="CS 102") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101"]


def test_bare_verb_asks_for_category_and_item(config: CombinedConfig):
    console = ScriptedConsole(["1", "2", "yes"])  # course -> CS 102 -> confirm

    run(console, Session(config=config), "delete")

    assert "Running: delete course 'CS 102'" in console.output
    assert DELETED.format(name="CS 102") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101"]


def test_category_given_asks_only_which_item(config: CombinedConfig):
    console = ScriptedConsole(["2", "yes"])  # CS 102 -> confirm

    run(console, Session(config=config), "delete course")

    assert DELETED.format(name="CS 102") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101"]


def test_unknown_category_is_rejected_before_anything_runs(config: CombinedConfig):
    console = ScriptedConsole([])

    with pytest.raises(CommandError, match="kind must be one of"):
        run(console, Session(config=config), "delete building B1")

    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_unknown_item_reports_and_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=config), "delete course CS999")

    assert console.output[-1] == NOT_FOUND.format(kind="course", name="CS999")
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_cancel_at_category_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["5"])  # Cancel

    run(console, Session(config=config), "delete")

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_cancel_at_item_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["2", "2"])  # room -> Cancel

    run(console, Session(config=config), "delete")

    assert console.output[-1] == CANCELLED
    assert [r.name for r in config.config.rooms] == ["Room 101"]


def test_declining_confirmation_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["no"])

    run(console, Session(config=config), 'delete course "CS 101"')

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_no_config_loaded_reports_and_asks_nothing():
    console = ScriptedConsole([])

    run(console, Session(config=None), 'delete course "CS 101"')
    run(console, Session(config=None), "delete")

    assert console.output == [NO_CONFIG, NO_CONFIG]


def test_delete_that_would_leave_config_invalid_is_rolled_back(config: CombinedConfig):
    # Dr. Smith teaches CS 101; removing her breaks CS 101's faculty reference.
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete faculty "Dr. Smith"')

    assert "Can't delete Dr. Smith" in console.output[-1]
    assert [f.name for f in config.config.faculty] == ["Dr. Smith", "Dr. Jones"]


def test_nothing_to_delete_reports_without_further_prompts(config_data: dict):
    config_data["config"]["labs"] = []
    for course in config_data["config"]["courses"]:
        course["lab"] = []
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole([])

    run(console, Session(config=config), "delete lab")

    assert console.output[-1] == NOTHING_TO_DELETE


def test_deleting_a_room_strips_it_from_courses_and_preferences(config_data: dict):
    config_data["config"]["rooms"].append({"name": "Room 102", "capacity": 30})
    config_data["config"]["courses"][0]["room"] = ["Room 101", "Room 102"]
    config_data["config"]["faculty"][0]["room_preferences"] = {"Room 102": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete room "Room 102"')

    assert DELETED.format(name="Room 102") in console.output
    assert [room.name for room in config.config.rooms] == ["Room 101"]
    assert config.config.courses[0].room == ["Room 101"]
    assert config.config.faculty[0].room_preferences == {}


def test_deleting_a_lab_strips_it_from_courses_and_preferences(config_data: dict):
    config_data["config"]["faculty"][0]["lab_preferences"] = {"Lab 101": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete lab "Lab 101"')

    assert DELETED.format(name="Lab 101") in console.output
    assert config.config.labs == []
    assert all(course.lab == [] for course in config.config.courses)
    assert config.config.faculty[0].lab_preferences == {}


def test_deleting_a_course_strips_it_from_conflicts_and_preferences(config_data: dict):
    config_data["config"]["faculty"][0]["course_preferences"] = {"CS 101": 5}
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete course "CS 101"')

    assert DELETED.format(name="CS 101") in console.output
    assert [course.course_id for course in config.config.courses] == ["CS 102"]
    assert config.config.courses[0].conflicts == []
    assert config.config.faculty[0].course_preferences == {}


def test_deleting_a_faculty_member_strips_them_from_courses(config_data: dict):
    config_data["config"]["courses"][0]["faculty"] = ["Dr. Smith", "Dr. Jones"]
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete faculty "Dr. Jones"')

    assert DELETED.format(name="Dr. Jones") in console.output
    assert [faculty.name for faculty in config.config.faculty] == ["Dr. Smith"]
    assert [course.faculty for course in config.config.courses] == [
        ["Dr. Smith"],
        ["Dr. Smith"],
    ]


def test_deleting_the_only_room_is_refused(config: CombinedConfig):
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete room "Room 101"')

    assert "Can't delete Room 101" in console.output[-1]
    assert [room.name for room in config.config.rooms] == ["Room 101"]
    assert config.config.courses[0].room == ["Room 101"]


# A course id names a course, not one offering of it: the realistic configuration lists
# CMSC 161 three times, once per section, and the sections differ in rooms and faculty.


def sections(config: CombinedConfig, course_id: str) -> list:
    return [course for course in config.config.courses if course.course_id == course_id]


def test_sections_sharing_a_course_id_are_listed_apart(example: CombinedConfig):
    console = ScriptedConsole(["1", "5", "yes"])  # course -> 2nd CMSC 161 -> confirm

    run(console, Session(config=example), "delete")

    assert "  4) CMSC 161 (section 1 of 3)" in console.output
    assert "  5) CMSC 161 (section 2 of 3)" in console.output
    assert "  6) CMSC 161 (section 3 of 3)" in console.output


def test_choosing_a_section_from_the_menu_deletes_only_that_one(example: CombinedConfig):
    console = ScriptedConsole(["1", "5", "yes"])  # course -> 2nd CMSC 161 -> confirm
    doomed = sections(example, "CMSC 161")[1]

    run(console, Session(config=example), "delete")

    assert "Running: delete course 'CMSC 161' --section 2" in console.output
    assert DELETED.format(name="CMSC 161 (section 2 of 3)") in console.output
    assert doomed not in sections(example, "CMSC 161")
    assert len(sections(example, "CMSC 161")) == 2


def test_section_option_deletes_only_that_section(example: CombinedConfig):
    console = ScriptedConsole(["yes"])
    survivors = [sections(example, "CMSC 161")[0], sections(example, "CMSC 161")[2]]

    run(console, Session(config=example), 'delete course "CMSC 161" --section 2')

    assert DELETED.format(name="CMSC 161 (section 2 of 3)") in console.output
    assert sections(example, "CMSC 161") == survivors


def test_a_shared_course_id_alone_is_refused_rather_than_guessed(example: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=example), 'delete course "CMSC 161"')

    assert console.output[-1] == AMBIGUOUS.format(count=3, name="CMSC 161")
    assert len(sections(example, "CMSC 161")) == 3


def test_section_outside_the_range_is_refused(example: CombinedConfig):
    console = ScriptedConsole([])

    run(console, Session(config=example), 'delete course "CMSC 161" --section 4')

    assert console.output[-1] == BAD_SECTION.format(count=3)
    assert len(sections(example, "CMSC 161")) == 3


def test_deleting_one_section_leaves_references_to_the_course_alone(example: CombinedConfig):
    # CMSC 140 conflicts with CMSC 161; two sections of CMSC 161 outlive the deletion.
    console = ScriptedConsole(["yes"])

    run(console, Session(config=example), 'delete course "CMSC 161" --section 2')

    assert all("CMSC 161" in course.conflicts for course in sections(example, "CMSC 140"))
    assert "CMSC 161" in example.config.faculty[0].course_preferences


def test_deleting_the_last_section_strips_references_to_the_course(example_data: dict):
    # CMSC 162 is listed once, and CMSC 140 conflicts with it.
    config = CombinedConfig.model_validate(example_data)
    console = ScriptedConsole(["yes"])

    run(console, Session(config=config), 'delete course "CMSC 162"')

    assert DELETED.format(name="CMSC 162") in console.output
    assert sections(config, "CMSC 162") == []
    assert all("CMSC 162" not in course.conflicts for course in config.config.courses)


def test_a_unique_name_needs_no_section(example: CombinedConfig):
    console = ScriptedConsole(["yes"])

    run(console, Session(config=example), 'delete faculty "Schwartz"')

    assert DELETED.format(name="Schwartz") in console.output
    assert "Schwartz" not in [faculty.name for faculty in example.config.faculty]


def test_courses_with_no_named_faculty_survive_a_faculty_deletion(example: CombinedConfig):
    # Most courses carry "faculty": null, meaning "derive from preferences".
    console = ScriptedConsole(["yes"])

    run(console, Session(config=example), 'delete faculty "Schwartz"')

    assert DELETED.format(name="Schwartz") in console.output
    assert any(course.faculty is None for course in example.config.courses)
