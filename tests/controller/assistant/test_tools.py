"""The assistant's tools: registration, argument checks, and each action through the app."""

import json

import pytest

from zimpasta.controller.assistant.tools import TOOLS, ToolResult

ROOM = {"name": "Room 201", "capacity": 30}


def run(app, name: str, **arguments) -> ToolResult:
    return TOOLS.dispatch(app, name, json.dumps(arguments))


def edit(app, *changes: dict) -> ToolResult:
    return run(app, "edit_configuration", changes=list(changes))


def failure(result: ToolResult) -> dict:
    assert result.error is not None, result.summary
    return dict(result.error)


def names(app, area: str) -> list[str]:
    return [item["name"] for item in app.workspace.items(area)]


# ---------------------------------------------------------------- registration


def test_every_required_operation_is_a_registered_tool():
    assert TOOLS.names() == [
        "inspect_configuration",
        "describe_fields",
        "edit_configuration",
        "new_configuration",
        "validate_configuration",
        "save_configuration",
        "generate_schedules",
        "generation_status",
    ]


def test_definitions_are_openai_functions_with_defined_arguments():
    definitions = {definition["name"]: definition for definition in TOOLS.definitions()}

    for definition in definitions.values():
        assert definition["type"] == "function"
        assert definition["description"]
        assert definition["parameters"]["type"] == "object"
        assert definition["parameters"]["additionalProperties"] is False
        assert "$defs" not in json.dumps(definition["parameters"])

    change = definitions["edit_configuration"]["parameters"]["properties"]["changes"]["items"]
    assert set(change["properties"]) == {"action", "area", "index", "item", "fields"}
    assert change["properties"]["action"]["enum"] == ["add", "update", "delete"]
    assert "time_slots" in change["properties"]["area"]["enum"]
    generate = definitions["generate_schedules"]["parameters"]["properties"]
    assert set(generate) == {"limit", "optimizer_flags"}


def test_two_tools_with_one_name_are_refused():
    from zimpasta.controller.assistant.tools import Tool, ToolRegistry

    tool = TOOLS.get("validate_configuration")
    assert tool is not None
    with pytest.raises(ValueError, match="Two tools"):
        ToolRegistry([tool, Tool(tool.name, "again", tool.arguments, tool.handler)])


# ----------------------------------------------------- unsupported or malformed


def test_an_unknown_tool_fails_and_lists_the_real_ones(app):
    result = TOOLS.dispatch(app, "run_shell", "{}")

    assert result.status == "failed"
    assert failure(result)["code"] == "unknown_tool"
    assert "edit_configuration" in result.summary


@pytest.mark.parametrize("arguments", ["{not json", "[1, 2]"])
def test_malformed_arguments_fail_without_running_anything(app, arguments):
    revision = app.workspace.revision

    result = TOOLS.dispatch(app, "edit_configuration", arguments)

    assert failure(result)["code"] == "invalid_arguments"
    assert app.workspace.revision == revision


@pytest.mark.parametrize(
    ("change", "missing"),
    [
        ({"action": "update", "area": "faculty", "fields": {"maximum_credits": 6}}, "index"),
        ({"action": "delete", "area": "rooms"}, "index"),
        ({"action": "add", "area": "rooms"}, "item"),
        ({"action": "update", "area": "rooms", "index": 0}, "fields"),
        ({"action": "delete", "area": "settings"}, "can only be updated"),
    ],
)
def test_missing_information_is_reported_as_such(app, change, missing):
    result = edit(app, change)

    assert result.status == "failed"
    assert failure(result)["code"] == "invalid_arguments"
    assert missing in result.summary
    assert failure(result)["issues"][0]["path"].startswith("changes.0")


def test_arguments_the_tool_does_not_define_are_refused(app):
    result = run(app, "validate_configuration", force=True)

    assert failure(result)["code"] == "invalid_arguments"
    assert "force" in failure(result)["issues"][0]["path"]


def test_an_unexpected_error_is_a_failure_not_a_crash(app, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(app, "validate_configuration", broken)

    result = run(app, "validate_configuration")

    assert failure(result)["code"] == "tool_failed"
    assert "disk on fire" not in result.summary


# ------------------------------------------------------------------ inspecting


def test_inspect_overview_reports_state_counts_and_saved(app):
    result = run(app, "inspect_configuration", area="overview")
    data = json.loads(result.for_model())

    assert result.ok
    assert data["status_of_configuration"] == "valid"
    assert data["saved"] is True
    assert data["counts"]["faculty"] == 2
    assert data["generation"]["state"] == "idle"


def test_inspect_an_area_lists_items_with_indexes(app):
    data = json.loads(run(app, "inspect_configuration", area="courses").for_model())

    assert [(item["index"], item["section"]) for item in data["items"]] == [
        (0, "CS 101.01"),
        (1, "CS 102.01"),
    ]


def test_inspect_sections(app):
    settings = json.loads(run(app, "inspect_configuration", area="settings").for_model())
    slots = json.loads(run(app, "inspect_configuration", area="time_slots").for_model())

    assert settings["settings"]["limit"] == 3
    assert "classes" not in slots["time_slots"] and "times" in slots["time_slots"]


def test_inspecting_with_nothing_open_explains_it(app):
    from zimpasta.controller import AppController

    empty = AppController(ai_client_factory=None)

    assert run(empty, "inspect_configuration", area="overview").ok
    for area in ("rooms", "settings"):
        result = run(empty, "inspect_configuration", area=area)
        assert failure(result)["code"] == "no_configuration"


def test_describe_fields_gives_the_library_schema_choices_and_an_example(app):
    data = json.loads(run(app, "describe_fields", area="faculty").for_model())

    assert "maximum_credits" in data["schema"]["properties"]
    assert "MON" in data["choices"]["weekdays"]
    assert data["example"]["name"] == "Dr. Smith"
    settings = json.loads(run(app, "describe_fields", area="settings").for_model())
    assert settings["choices"]["optimizer_flags"]
    slots = json.loads(run(app, "describe_fields", area="time_slots").for_model())
    assert "classes" not in slots["schema"]["properties"]


# --------------------------------------------------------------------- editing


def test_a_valid_edit_is_applied_through_the_library(app):
    revision = app.workspace.revision

    result = edit(app, {"action": "add", "area": "rooms", "item": ROOM})

    assert result.ok
    assert result.summary == "Added room Room 201."
    assert names(app, "rooms") == ["Room 101", "Room 201"]
    assert app.workspace.revision == revision + 1
    assert app.workspace.dirty
    assert json.loads(result.for_model())["saved_to_file"] is False


def test_a_rejected_edit_keeps_the_last_valid_configuration(app):
    before = app.workspace.document()

    result = edit(
        app, {"action": "update", "area": "faculty", "index": 0, "fields": {"minimum_credits": 99}}
    )

    assert result.status == "failed"
    assert failure(result)["code"] == "edit_rejected"
    assert result.summary.startswith("Nothing was changed. Change 1 (update faculty #0)")
    assert failure(result)["issues"][0]["field"]
    assert app.workspace.document() == before
    assert not app.workspace.dirty


def test_a_combined_edit_is_applied_entirely_or_not_at_all(app):
    before = app.workspace.document()
    bad_course = {
        "course_id": "CS 300",
        "credits": 3,
        "capacity": 20,
        "room": ["Nowhere 999"],
        "lab": [],
        "conflicts": [],
        "faculty": ["Dr. Smith"],
    }

    result = edit(
        app,
        {"action": "add", "area": "rooms", "item": ROOM},
        {"action": "add", "area": "courses", "item": bad_course},
    )

    assert result.status == "failed"
    assert failure(result)["change"] == 2
    assert app.workspace.document() == before
    assert app.workspace.changes == ()


def test_an_update_changes_only_the_named_fields_and_renames_references(app):
    result = edit(
        app, {"action": "update", "area": "faculty", "index": 1, "fields": {"name": "Dr. Lee"}}
    )

    assert result.ok
    assert names(app, "faculty") == ["Dr. Smith", "Dr. Lee"]
    assert app.workspace.item("faculty", 1)["maximum_credits"] > 0
    assert app.workspace.item("courses", 1)["faculty"] == ["Dr. Smith", "Dr. Lee"]


def test_settings_time_slots_and_pattern_meetings_can_be_updated(app):
    meetings = app.workspace.item("patterns", 0)["meetings"]

    result = edit(
        app,
        {"action": "update", "area": "settings", "fields": {"limit": 7}},
        {"action": "update", "area": "time_slots", "fields": {"max_time_gap": 45}},
        {"action": "update", "area": "patterns", "index": 0, "fields": {"meetings": meetings}},
    )

    assert result.ok, result.error
    assert app.workspace.document()["limit"] == 7
    assert app.workspace.document()["time_slot_config"]["max_time_gap"] == 45


# -------------------------------------------------------------------- deleting


def test_a_delete_with_references_waits_for_confirmation(app):
    before = app.workspace.document()

    result = edit(app, {"action": "delete", "area": "faculty", "index": 1})

    assert result.status == "waiting"
    pending = result.pending
    assert pending is not None and pending.kind == "confirm"
    assert pending.prompt == "Delete faculty member Dr. Jones and 1 reference to it?"
    assert any("CS 102.01" in line for line in pending.details)
    assert app.workspace.document() == before
    assert json.loads(result.for_model())["waiting_for_user"]["kind"] == "confirm"

    assert pending.run is not None
    confirmed = pending.run()

    assert confirmed.ok
    assert names(app, "faculty") == ["Dr. Smith"]
    assert app.workspace.item("courses", 1)["faculty"] == ["Dr. Smith"]


def test_a_delete_other_items_depend_on_is_refused(app):
    before = app.workspace.document()

    result = edit(app, {"action": "delete", "area": "rooms", "index": 0})

    assert result.status == "failed"
    assert failure(result)["code"] == "delete_blocked"
    assert [ref["label"] for ref in failure(result)["impact"]["blocking"]] == [
        "CS 101.01",
        "CS 102.01",
    ]
    assert app.workspace.document() == before


def test_indexes_mean_the_configuration_before_the_batch(app):
    edit(app, {"action": "add", "area": "rooms", "item": ROOM})
    edit(app, {"action": "add", "area": "rooms", "item": {"name": "Room 301", "capacity": 10}})

    result = edit(
        app,
        {"action": "delete", "area": "rooms", "index": 1},
        {"action": "delete", "area": "rooms", "index": 2},
    )
    assert result.pending is not None and result.pending.run is not None
    assert result.pending.run().ok

    assert names(app, "rooms") == ["Room 101"]


def test_deleting_one_item_twice_is_refused(app):
    result = edit(
        app,
        {"action": "delete", "area": "faculty", "index": 1},
        {"action": "delete", "area": "faculty", "index": 1},
    )

    assert failure(result)["code"] == "invalid_arguments"


# ------------------------------------------------- new, validate, save, generate


def test_new_configuration_is_immediate_when_everything_is_saved(app):
    result = run(app, "new_configuration")

    assert result.ok
    assert app.workspace.status.value == "incomplete"


def test_new_configuration_over_unsaved_changes_waits_for_confirmation(app):
    edit(app, {"action": "add", "area": "rooms", "item": ROOM})

    result = run(app, "new_configuration")

    assert result.status == "waiting"
    assert result.pending is not None and result.pending.details == ("Added room Room 201",)
    assert "Room 201" in names(app, "rooms")
    assert result.pending.run is not None and result.pending.run().ok
    assert app.workspace.status.value == "incomplete"


def test_validate_uses_the_library(app):
    result = run(app, "validate_configuration")

    assert result.ok and json.loads(result.for_model())["valid"] is True
    run(app, "new_configuration")
    incomplete = json.loads(run(app, "validate_configuration").for_model())
    assert incomplete["valid"] is False and incomplete["problems"]


def test_save_prepares_the_file_and_waits_for_the_user(app):
    edit(app, {"action": "add", "area": "rooms", "item": ROOM})

    result = run(app, "save_configuration")

    assert result.status == "waiting"
    assert result.pending is not None and result.pending.kind == "save"
    assert result.pending.revision == app.workspace.revision
    assert app.workspace.dirty
    assert "Nothing has been saved yet" in result.for_model()


def test_save_needs_a_valid_configuration(app):
    run(app, "new_configuration")

    result = run(app, "save_configuration")

    assert failure(result)["code"] == "configuration_incomplete"


def test_generate_starts_the_job_and_results_reach_the_viewer(app):
    result = run(app, "generate_schedules", limit=2)

    assert result.ok
    assert json.loads(result.for_model())["generation"]["limit"] == 2
    assert app.job.wait(10).state.value == "succeeded"
    assert app.schedule_summary()["count"] == 2
    status = json.loads(run(app, "generation_status").for_model())
    assert status["generation"]["state"] == "succeeded" and status["schedules"] == 2


def test_generate_reports_invalid_overrides_and_busy_runs(app):
    bad = run(app, "generate_schedules", optimizer_flags=["go_fast"])
    assert failure(bad)["code"] == "invalid_overrides"

    from zimpasta.model.generation_job import GenerationBusy

    def busy(**kwargs):
        raise GenerationBusy()

    app.start_generation = busy
    assert failure(run(app, "generate_schedules"))["code"] == "generation_running"
