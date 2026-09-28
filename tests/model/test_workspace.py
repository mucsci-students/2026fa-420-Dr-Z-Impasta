"""The configuration workspace: lifecycle, validated edits, deletes, and unsaved changes."""

import copy
import json

import pytest
from scheduler import CombinedConfig, TimeSlotConfig

from tests.helpers import EXAMPLE_CONFIG
from zimpasta.model.defaults import default_time_slot_config, empty_configuration
from zimpasta.model.workspace import (
    ConfigStatus,
    ConfigWorkspace,
    DeleteBlocked,
    EditRejected,
    InvalidFile,
    ItemNotFound,
    NoConfiguration,
    NotValid,
    UnsavedChanges,
)

ROOM = {"name": "Room 201", "capacity": 30}
LAB = {"name": "Lab 201", "capacity": 20}
FACULTY = {
    "name": "Dr. Lee",
    "maximum_credits": 9,
    "minimum_credits": 0,
    "unique_course_limit": 2,
    "times": {"MON": ["08:00-18:00"], "WED": ["08:00-18:00"], "FRI": ["08:00-18:00"]},
}


def course(course_id="CS 201", *, rooms=("Room 201",), faculty=("Dr. Lee",), credits=3):
    return {
        "course_id": course_id,
        "credits": credits,
        "capacity": 20,
        "room": list(rooms),
        "lab": [],
        "conflicts": [],
        "faculty": list(faculty),
    }


@pytest.fixture
def workspace(config_data) -> ConfigWorkspace:
    """A workspace holding the two-course test fixture, freshly loaded."""
    ws = ConfigWorkspace()
    ws.load_text(json.dumps(config_data), filename="minimal.json")
    return ws


@pytest.fixture
def example_workspace() -> ConfigWorkspace:
    ws = ConfigWorkspace()
    ws.load_text(EXAMPLE_CONFIG.read_text(encoding="utf-8"), filename="sample_config.json")
    return ws


# ------------------------------------------------------------------ defaults


def test_default_time_slots_are_valid_for_the_library():
    TimeSlotConfig.model_validate(default_time_slot_config())
    assert default_time_slot_config() is not default_time_slot_config()


def test_empty_configuration_only_lacks_required_items():
    ws = ConfigWorkspace()
    ws.new()
    assert ws.document()["time_slot_config"] == default_time_slot_config()
    assert empty_configuration()["config"]["rooms"] == []


# ------------------------------------------------------------------ lifecycle


def test_nothing_open_at_first():
    ws = ConfigWorkspace()

    assert ws.status is ConfigStatus.NONE
    assert ws.document() is None
    with pytest.raises(NoConfiguration):
        ws.add("rooms", ROOM)
    with pytest.raises(NoConfiguration):
        ws.export_text()


def test_new_configuration_is_incomplete_with_three_missing_items():
    ws = ConfigWorkspace()

    ws.new()

    assert ws.status is ConfigStatus.INCOMPLETE
    assert [problem.message for problem in ws.issues] == [
        "Add at least one room.",
        "Add at least one course.",
        "Add at least one faculty member.",
    ]
    assert ws.counts()["patterns"] == 16
    assert not ws.dirty
    with pytest.raises(NotValid):
        ws.export_text()


def test_building_a_new_configuration_until_it_is_valid():
    ws = ConfigWorkspace()
    ws.new()

    ws.add("rooms", ROOM)
    assert ws.status is ConfigStatus.INCOMPLETE
    ws.add("faculty", FACULTY)
    assert [problem.area for problem in ws.issues] == ["courses"]
    change = ws.add("courses", course())

    assert ws.status is ConfigStatus.VALID
    assert ws.issues == ()
    assert isinstance(ws.config, CombinedConfig)
    assert change.summary == "Added course section CS 201.01"
    assert [c.action for c in ws.changes] == ["added", "added", "added"]
    assert ws.dirty


def test_incomplete_configuration_still_enforces_item_rules():
    ws = ConfigWorkspace()
    ws.new()
    revision = ws.revision

    with pytest.raises(EditRejected) as caught:
        ws.add("rooms", {"name": "Tiny", "capacity": 0})

    assert caught.value.issues[0].area == "rooms"
    assert caught.value.issues[0].field == "capacity"
    assert ws.revision == revision
    assert ws.counts()["rooms"] == 0


def test_cross_item_problems_surface_on_the_edit_that_completes_the_configuration():
    ws = ConfigWorkspace()
    ws.new()
    ws.add("rooms", ROOM)
    ws.add("courses", course(rooms=("Nowhere",)))

    with pytest.raises(EditRejected) as caught:
        ws.add("faculty", FACULTY)

    assert ws.status is ConfigStatus.INCOMPLETE
    assert any(problem.area == "courses" for problem in caught.value.issues)

    ws.replace("courses", 0, course())
    ws.add("faculty", FACULTY)
    assert ws.status is ConfigStatus.VALID


def test_load_valid_configuration(config_data):
    ws = ConfigWorkspace()

    ws.load_text(json.dumps(config_data), filename="minimal.json")

    assert ws.status is ConfigStatus.VALID
    assert ws.name == "minimal.json"
    assert not ws.dirty
    assert ws.changes == ()
    assert ws.counts() == {
        "rooms": 1,
        "labs": 1,
        "sections": 2,
        "courses": 2,
        "faculty": 2,
        "patterns": 2,
        "enabled_patterns": 2,
    }


def test_malformed_json_is_rejected_and_the_previous_configuration_kept(workspace):
    before = workspace.document()

    with pytest.raises(InvalidFile) as caught:
        workspace.load_text('{"config": ', filename="broken.json")

    assert caught.value.code == "malformed_json"
    assert "line 1" in caught.value.message
    assert workspace.document() == before
    assert workspace.name == "minimal.json"


def test_schema_invalid_file_is_rejected_with_located_issues(workspace, config_data):
    bad = copy.deepcopy(config_data)
    bad["config"]["rooms"][0]["capacity"] = -5
    before = workspace.document()

    with pytest.raises(InvalidFile) as caught:
        workspace.load_text(json.dumps(bad), filename="bad.json")

    assert caught.value.code == "invalid_configuration"
    assert (caught.value.issues[0].area, caught.value.issues[0].field) == ("rooms", "capacity")
    assert workspace.document() == before


def test_json_that_is_not_an_object_is_rejected(workspace):
    with pytest.raises(InvalidFile) as caught:
        workspace.load_text("[1, 2, 3]", filename="list.json")

    assert caught.value.code == "invalid_configuration"


def test_unreadable_file(tmp_path):
    ws = ConfigWorkspace()

    with pytest.raises(InvalidFile) as caught:
        ws.load_file(tmp_path / "missing.json")
    assert caught.value.code == "unreadable_file"

    binary = tmp_path / "binary.json"
    binary.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(InvalidFile) as caught:
        ws.load_file(binary)
    assert caught.value.code == "unreadable_file"


def test_load_file_reads_utf8(config_file):
    ws = ConfigWorkspace()

    ws.load_file(config_file)

    assert ws.status is ConfigStatus.VALID
    assert ws.name == "config.json"


def test_loading_over_unsaved_changes_needs_confirmation(workspace, config_data):
    workspace.update_settings({"limit": 5})

    with pytest.raises(UnsavedChanges) as caught:
        workspace.load_text(json.dumps(config_data), filename="other.json")

    assert [change.summary for change in caught.value.changes] == ["Settings: limit 3 → 5"]
    assert workspace.name == "minimal.json"

    workspace.load_text(json.dumps(config_data), filename="other.json", discard_changes=True)
    assert workspace.name == "other.json"
    assert not workspace.dirty


def test_invalid_file_is_reported_before_asking_about_unsaved_changes(workspace):
    workspace.update_settings({"limit": 5})

    with pytest.raises(InvalidFile):
        workspace.load_text("not json", filename="broken.json")


def test_new_over_unsaved_changes_needs_confirmation(workspace):
    workspace.update_settings({"limit": 5})

    with pytest.raises(UnsavedChanges):
        workspace.new()

    workspace.new(discard_changes=True)
    assert workspace.status is ConfigStatus.INCOMPLETE


def test_export_round_trips_and_is_utf8(example_workspace):
    exported = example_workspace.export_text()

    assert exported.filename == "sample_config.json"
    assert exported.revision == example_workspace.revision
    exported.content.encode("utf-8")
    again = ConfigWorkspace()
    again.load_text(exported.content, filename="again.json")
    assert again.config == example_workspace.config
    assert CombinedConfig.model_validate_json(exported.content) == example_workspace.config


def test_mark_saved_clears_changes_up_to_that_revision(workspace):
    workspace.update_settings({"limit": 4})
    saved_at = workspace.revision
    workspace.update_settings({"limit": 6})

    workspace.mark_saved(saved_at, "saved.json")

    assert workspace.dirty
    assert [change.summary for change in workspace.changes] == ["Settings: limit 4 → 6"]
    assert workspace.name == "saved.json"

    workspace.mark_saved(workspace.revision)
    assert not workspace.dirty
    assert workspace.changes == ()


def test_validate_reports_current_state(workspace):
    report = workspace.validate()

    assert report.valid
    assert report.to_dict()["issues"] == []


# ------------------------------------------------------------------ editing


def test_failed_edit_leaves_the_valid_configuration_untouched(workspace):
    before = workspace.document()
    revision = workspace.revision
    faculty = workspace.item("faculty", 0)
    faculty["minimum_credits"] = 99

    with pytest.raises(EditRejected) as caught:
        workspace.replace("faculty", 0, faculty)

    problem = caught.value.issues[0]
    assert (problem.area, problem.index, problem.field) == ("faculty", 0, "minimum_credits")
    assert caught.value.message.startswith("The change was not applied:")
    assert workspace.document() == before
    assert workspace.revision == revision
    assert workspace.changes == ()


def test_editing_a_copy_and_discarding_it_changes_nothing(workspace):
    before = workspace.document()

    draft = workspace.item("rooms", 0)
    draft["capacity"] = 1
    workspace.items("courses")[0]["credits"] = 99

    assert workspace.document() == before


@pytest.mark.parametrize(
    ("area", "item"),
    [
        ("rooms", ROOM),
        ("labs", LAB),
        ("courses", course(rooms=("Room 101",), faculty=("Dr. Smith",))),
        (
            "faculty",
            {**FACULTY, "times": {"MON": ["08:00-18:00"]}},
        ),
        (
            "patterns",
            {"credits": 3, "meetings": [{"day": "TUE", "duration": 150}]},
        ),
    ],
)
def test_add_to_every_area(workspace, area, item):
    before = len(workspace.items(area))

    change = workspace.add(area, item)

    assert len(workspace.items(area)) == before + 1
    assert change.action == "added"
    assert workspace.status is ConfigStatus.VALID


def test_update_every_area(workspace):
    room = workspace.item("rooms", 0)
    room["capacity"] = 45
    assert workspace.replace("rooms", 0, room).summary == "Room Room 101: capacity 40 → 45"

    lab = workspace.item("labs", 0)
    lab["features"] = ["linux"]
    assert workspace.replace("labs", 0, lab).summary == "Lab Lab 101: features changed"

    section = workspace.item("courses", 0)
    section["capacity"] = 18
    workspace.replace("courses", 0, section)

    member = workspace.item("faculty", 1)
    member["maximum_credits"] = 9
    assert "maximum_credits 12 → 9" in workspace.replace("faculty", 1, member).summary

    pattern = workspace.item("patterns", 0)
    pattern["start_time"] = "09:00"
    workspace.replace("patterns", 0, pattern)

    workspace.update_time_slots({"max_time_gap": 20})
    workspace.update_settings({"optimizer_flags": ["same_room"]})

    config = workspace.config
    assert config.config.rooms[0].capacity == 45
    assert config.config.labs[0].features == {"linux"}
    assert config.config.courses[0].capacity == 18
    assert config.config.faculty[1].maximum_credits == 9
    assert config.time_slot_config.classes[0].start_time is not None
    assert config.time_slot_config.max_time_gap == 20
    assert [flag.value for flag in config.optimizer_flags] == ["same_room"]
    assert len(workspace.changes) == 7


def test_delete_from_every_area(example_workspace):
    ws = example_workspace
    counts = ws.counts()

    ws.remove("courses", 0)
    ws.remove("rooms", [r["name"] for r in ws.items("rooms")].index("Roddy 147"))
    ws.add("labs", LAB)
    ws.remove("labs", 2)
    rogers = [member["name"] for member in ws.items("faculty")].index("Rogers")
    ws.remove("faculty", rogers)
    disabled = [p.get("disabled") for p in ws.items("patterns")].index(True)
    ws.remove("patterns", disabled)

    after = ws.counts()
    assert after["sections"] == counts["sections"] - 1
    assert after["rooms"] == counts["rooms"] - 1
    assert after["labs"] == counts["labs"]
    assert after["faculty"] == counts["faculty"] - 1
    assert after["patterns"] == counts["patterns"] - 1
    assert ws.status is ConfigStatus.VALID


def test_delete_blocked_by_references_changes_nothing(workspace):
    before = workspace.document()

    impact = workspace.delete_impact("rooms", 0)
    assert not impact.can_delete
    assert [ref.label for ref in impact.blocking] == ["CS 101.01", "CS 102.01"]

    with pytest.raises(DeleteBlocked) as caught:
        workspace.remove("rooms", 0)

    assert caught.value.impact == impact
    assert "2 sections depend on it" in caught.value.message
    assert workspace.document() == before


def test_delete_cascades_optional_references(workspace):
    impact = workspace.delete_impact("faculty", 1)
    assert impact.can_delete
    assert [ref.field for ref in impact.cascades] == ["faculty"]

    change, applied = workspace.remove("faculty", 1)

    assert applied == impact
    assert change.summary == "Removed faculty member Dr. Jones and 1 reference to it"
    assert workspace.item("courses", 1)["faculty"] == ["Dr. Smith"]


def test_a_valid_configuration_can_not_become_incomplete(workspace):
    workspace.remove("courses", 1)

    impact = workspace.delete_impact("courses", 0)

    assert not impact.can_delete
    assert impact.problems[0].message == "Add at least one course."
    with pytest.raises(DeleteBlocked):
        workspace.remove("courses", 0)
    assert workspace.counts()["sections"] == 1


def test_renaming_updates_references(workspace):
    room = workspace.item("rooms", 0)
    room["name"] = "Room 201"

    change = workspace.replace("rooms", 0, room)

    assert change.summary == "Room Room 201: name Room 101 → Room 201 (2 references updated)"
    assert all(section["room"] == ["Room 201"] for section in workspace.items("courses"))
    assert workspace.status is ConfigStatus.VALID


def test_renaming_one_of_several_sections_keeps_references(example_workspace):
    section = example_workspace.item("courses", 0)
    section["course_id"] = "CMSC 141"
    section["faculty"] = ["Hardy"]

    example_workspace.replace("courses", 0, section)

    labels = example_workspace.section_labels()
    assert labels[:2] == ["CMSC 141.01", "CMSC 140.01"]
    assert any("CMSC 140" in c["conflicts"] for c in example_workspace.items("courses"))


def test_settings_validation_and_unknown_fields(workspace):
    with pytest.raises(EditRejected) as caught:
        workspace.update_settings({"limit": 0})
    assert caught.value.issues[0].area == "settings"

    with pytest.raises(EditRejected) as caught:
        workspace.update_settings({"optimizer_flags": ["go_fast"]})
    assert caught.value.issues[0].field == "optimizer_flags"

    with pytest.raises(EditRejected) as caught:
        workspace.update_time_slots({"classes": []})
    assert caught.value.issues[0].code == "unknown_field"


def test_bad_addresses_and_payloads(workspace):
    with pytest.raises(ItemNotFound):
        workspace.item("rooms", 5)
    with pytest.raises(ItemNotFound):
        workspace.item("buildings", 0)
    with pytest.raises(ItemNotFound):
        workspace.remove("rooms", -1)
    with pytest.raises(EditRejected):
        workspace.add("rooms", ["not", "an", "object"])


def test_snapshot(workspace):
    workspace.update_settings({"limit": 2})

    snapshot = workspace.snapshot()

    assert snapshot["status"] == "valid"
    assert snapshot["name"] == "minimal.json"
    assert snapshot["dirty"] is True
    assert snapshot["changes"][0]["area"] == "settings"
    assert snapshot["counts"]["sections"] == 2
    assert snapshot["validated_at"]
