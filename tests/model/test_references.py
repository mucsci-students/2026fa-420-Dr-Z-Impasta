import json

import pytest

from tests.helpers import EXAMPLE_CONFIG
from zimpasta.model.references import (
    apply_delete,
    apply_rename,
    delete_impact,
    item_label,
    pattern_label,
    section_labels,
)


@pytest.fixture
def example() -> dict:
    return json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))


def room_index(document, name):
    return [room["name"] for room in document["config"]["rooms"]].index(name)


def test_section_labels_number_repeated_course_ids(example):
    labels = section_labels(example["config"]["courses"])

    assert labels[:3] == ["CMSC 140.01", "CMSC 140.02", "CMSC 152.01"]
    assert labels.count("CMSC 161.03") == 1


def test_explicit_section_id_is_used():
    courses = [{"course_id": "CS 1", "section_id": "A"}, {"course_id": "CS 1", "section_id": None}]

    assert section_labels(courses) == ["CS 1.A", "CS 1.02"]


def test_item_labels(example):
    assert item_label(example, "rooms", 0) == "Roddy 136"
    assert item_label(example, "courses", 1) == "CMSC 140.02"
    assert item_label(example, "faculty", 0) == "Zoppetti"
    assert pattern_label(example["time_slot_config"]["classes"][3]) == "4 credits: MON (lab), WED"


def test_room_that_is_some_sections_only_room_is_blocked(example):
    impact = delete_impact(example, "rooms", room_index(example, "Roddy 136"))

    blocked = {reference.label for reference in impact.blocking}
    assert blocked == {"CMSC 161.01", "CMSC 362.01", "CMSC 476.01"}
    assert all(reference.field == "room" for reference in impact.blocking)
    assert not impact.can_delete
    cascade_fields = {reference.field for reference in impact.cascades}
    assert cascade_fields == {"room", "room_preferences"}
    assert sum(ref.field == "room_preferences" for ref in impact.cascades) == 9


def test_unreferenced_or_optional_room_cascades(example):
    impact = delete_impact(example, "rooms", room_index(example, "Roddy 147"))

    assert impact.blocking == ()
    assert impact.can_delete
    assert impact.cascades

    after = apply_delete(example, "rooms", room_index(example, "Roddy 147"))

    names = [room["name"] for room in after["config"]["rooms"]]
    assert "Roddy 147" not in names
    for course in after["config"]["courses"]:
        assert "Roddy 147" not in course["room"]
    for member in after["config"]["faculty"]:
        assert "Roddy 147" not in member.get("room_preferences", {})
    assert len(example["config"]["rooms"]) == 3


def test_only_lab_blocks_and_shared_lab_cascades(example):
    labs = [lab["name"] for lab in example["config"]["labs"]]

    linux = delete_impact(example, "labs", labs.index("Linux"))
    mac = delete_impact(example, "labs", labs.index("Mac"))

    assert "CMSC 161.01" in {reference.label for reference in linux.blocking}
    assert "CMSC 420.01" in {reference.label for reference in mac.blocking}
    assert "CMSC 152.01" in {reference.label for reference in mac.cascades}


def test_sole_faculty_candidate_blocks(example):
    names = [member["name"] for member in example["config"]["faculty"]]

    impact = delete_impact(example, "faculty", names.index("Zoppetti"))

    assert [reference.label for reference in impact.blocking] == ["CMSC 161.01"]


def test_faculty_among_several_candidates_cascades_and_never_leaves_an_empty_list(config_data):
    impact = delete_impact(config_data, "faculty", 1)
    assert impact.blocking == ()
    assert [reference.label for reference in impact.cascades] == ["CS 102.01"]

    after = apply_delete(config_data, "faculty", 1)

    assert after["config"]["courses"][1]["faculty"] == ["Dr. Smith"]

    config_data["config"]["courses"][1]["faculty"] = ["Dr. Jones"]
    after = apply_delete(config_data, "faculty", 1)
    assert after["config"]["courses"][1]["faculty"] is None


def test_deleting_one_of_several_sections_touches_no_references(example):
    impact = delete_impact(example, "courses", 0)

    assert impact.blocking == impact.cascades == ()

    after = apply_delete(example, "courses", 0)
    assert section_labels(after["config"]["courses"])[0] == "CMSC 140.01"
    assert any("CMSC 140" in course["conflicts"] for course in after["config"]["courses"])


def test_deleting_the_last_section_removes_conflicts_and_preferences(example):
    labels = section_labels(example["config"]["courses"])
    index = labels.index("CMSC 362.01")

    impact = delete_impact(example, "courses", index)
    after = apply_delete(example, "courses", index)

    assert impact.blocking == ()
    assert {reference.field for reference in impact.cascades} == {"conflicts", "course_preferences"}
    assert all("CMSC 362" not in course["conflicts"] for course in after["config"]["courses"])
    assert all(
        "CMSC 362" not in member.get("course_preferences", {})
        for member in after["config"]["faculty"]
    )


def test_patterns_have_no_name_references(example):
    impact = delete_impact(example, "patterns", 0)

    assert impact.blocking == impact.cascades == ()
    assert len(apply_delete(example, "patterns", 0)["time_slot_config"]["classes"]) == 15


def test_rename_updates_lists_and_preference_keys_in_place(example):
    after, count = apply_rename(example, "rooms", "Roddy 136", "Roddy 999")

    assert count > 0
    zoppetti = after["config"]["faculty"][0]
    assert list(zoppetti["room_preferences"])[0] == "Roddy 999"
    assert all("Roddy 136" not in course["room"] for course in after["config"]["courses"])
    assert example["config"]["faculty"][0]["room_preferences"].get("Roddy 136") is not None


def test_rename_course_id_updates_conflicts_and_preferences(example):
    after, count = apply_rename(example, "courses", "CMSC 362", "CMSC 363")

    assert count == 5
    assert "CMSC 363" in after["config"]["faculty"][0]["course_preferences"]
