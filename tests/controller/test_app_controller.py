"""Controller use cases: what each GUI action does, independent of HTTP."""

import json

import pytest

from zimpasta.model.generation_job import InvalidOverrides, JobState
from zimpasta.model.workspace import EditRejected, NoConfiguration, NotValid, UnsavedChanges

TIMEOUT = 10


@pytest.fixture
def loaded(controller, config_data):
    controller.load_configuration("minimal.json", json.dumps(config_data))
    return controller


def generate(controller, **overrides) -> dict:
    controller.start_generation(**overrides)
    controller.job.wait(TIMEOUT)
    return controller.generation_status()


def test_state_before_anything_is_open(controller):
    state = controller.state()

    assert state["config"]["status"] == "none"
    assert state["generation"]["state"] == "idle"
    assert state["schedules"]["count"] == 0


def test_applying_a_valid_form_change(loaded):
    room = loaded.get_item("rooms", 0)["item"]
    room["capacity"] = 55

    result = loaded.replace_item("rooms", 0, room)

    assert result["change"]["summary"] == "Room Room 101: capacity 40 → 55"
    assert result["document"]["config"]["rooms"][0]["capacity"] == 55
    assert result["state"]["dirty"] is True


def test_rejecting_an_invalid_form_change_keeps_the_configuration(loaded):
    before = loaded.configuration()
    course = loaded.get_item("courses", 0)["item"]
    course["room"] = ["Nowhere"]

    with pytest.raises(EditRejected) as caught:
        loaded.replace_item("courses", 0, course)

    assert caught.value.issues[0].area == "courses"
    assert loaded.configuration() == before


def test_load_save_round_trip(loaded):
    loaded.update_settings({"limit": 2})
    exported = loaded.export_configuration()

    state = loaded.mark_configuration_saved(exported.revision, "saved.json")

    assert state["dirty"] is False
    assert state["name"] == "saved.json"
    reloaded = loaded.load_configuration("saved.json", exported.content)
    assert reloaded["document"]["limit"] == 2


def test_loading_over_unsaved_changes_needs_confirmation(loaded, config_data):
    loaded.update_settings({"limit": 2})

    with pytest.raises(UnsavedChanges):
        loaded.load_configuration("other.json", json.dumps(config_data))

    result = loaded.load_configuration("other.json", json.dumps(config_data), discard_changes=True)
    assert result["state"]["name"] == "other.json"


@pytest.mark.parametrize(
    ("sent", "kept"),
    [("C:\\Users\\me\\spring.json", "spring.json"), ("../../etc/passwd", "passwd")],
)
def test_only_the_file_name_is_kept(controller, config_data, sent, kept):
    result = controller.load_configuration(sent, json.dumps(config_data))

    assert result["state"]["name"] == kept


def test_new_configuration_and_validation(controller):
    result = controller.new_configuration()

    assert result["state"]["status"] == "incomplete"
    report = controller.validate_configuration()["report"]
    assert report["valid"] is False
    assert len(report["issues"]) == 3


def test_generation_needs_a_valid_configuration(controller):
    with pytest.raises(NoConfiguration):
        controller.start_generation()

    controller.new_configuration()
    with pytest.raises(NotValid):
        controller.start_generation()


def test_generation_moves_results_into_the_viewer(loaded, fake_factory):
    status = generate(loaded, limit=2, optimizer_flags=["same_room"])

    assert status["state"] == JobState.SUCCEEDED
    assert status["config_name"] == "minimal.json"
    assert status["settings"]["limit_overridden"] is True
    summary = loaded.schedule_summary()
    assert summary["count"] == 2
    assert summary["source"] == "generated"
    assert summary["name"] == "minimal.json"
    assert [flag.value for flag in fake_factory.last_config.optimizer_flags] == ["same_room"]


def test_overrides_do_not_change_the_configuration(loaded):
    generate(loaded, limit=1, optimizer_flags=["pack_rooms"])

    document = loaded.configuration()["document"]
    assert document["limit"] == 3
    assert document["optimizer_flags"] == []
    assert loaded.state()["config"]["dirty"] is False


def test_invalid_override_starts_nothing(loaded):
    with pytest.raises(InvalidOverrides):
        loaded.start_generation(limit=0)

    assert loaded.generation_status()["state"] == "idle"


def test_generating_again_replaces_results_and_clear_empties_them(loaded):
    generate(loaded, limit=2)
    generate(loaded, limit=1)

    assert loaded.schedule_summary()["count"] == 1
    assert loaded.clear_schedules()["count"] == 0


def test_schedule_import_and_export(loaded):
    generate(loaded, limit=2)
    everything = loaded.export_schedules("all", "json")
    one = loaded.export_schedules(2, "json")
    as_csv = loaded.export_schedules("all", "csv")

    summary = loaded.import_schedules("C:\\exports\\" + everything.filename, everything.content)
    assert summary["count"] == 2
    assert summary["source"] == "imported"
    assert summary["name"] == everything.filename
    assert loaded.import_schedules(one.filename, one.content)["count"] == 1
    assert as_csv.media_type == "text/csv"


def test_selecting_room_and_faculty_views(loaded):
    generate(loaded, limit=2)

    rooms = loaded.schedule_view(1, "room")
    faculty = loaded.schedule_view(1, "faculty")

    assert {group["kind"] for group in rooms["groups"]} == {"room", "lab"}
    assert {group["kind"] for group in faculty["groups"]} == {"faculty"}
    assert rooms["totals"] == faculty["totals"]


def test_options_and_schema_come_from_the_library(controller):
    assert controller.options()["weekdays"] == ["MON", "TUE", "WED", "THU", "FRI"]
    assert "CombinedConfig" in controller.schema()["title"]
