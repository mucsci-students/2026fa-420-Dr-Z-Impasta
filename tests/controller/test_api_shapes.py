"""The field names of every API reply the GUI reads, so a rename can't break it silently.

The frontend (``frontend/src``) reads these replies as plain JavaScript objects, so nothing
else notices when a field is renamed or removed here. Each shape below lists the exact
fields of one reply and names the frontend files that read them. If a test fails:

- You renamed or removed a field on purpose: update the shape here *and* every frontend
  file listed next to it.
- You added a field: add it to the shape, so the frontend can rely on it too.

Only field names are checked, not their values. Replies the frontend ignores (for example
the bodies of edits, which it follows with a refresh) and the configuration ``document``
(the scheduler library's own file format) aren't covered here.
"""

import json
import re
from functools import partial

import pytest
from fastapi.testclient import TestClient

from tests.controller.conftest import BASE_URL
from tests.helpers import FakeAIClient, calling, saying, tool_call
from zimpasta.controller import AppController, create_app
from zimpasta.controller.assistant import AIError
from zimpasta.controller.assistant.tools import TOOLS
from zimpasta.model import references as refs
from zimpasta.model.generate import generation_steps

TIMEOUT = 10

# ------------------------------------------------------------------- the shapes
#
# A shape is a set of field names (an object whose values aren't checked), a dict from
# field name to the shape of its value (None: not checked), or a one-item list holding
# the shape of every item in a list.

ISSUE = {"path", "code", "message", "area", "index", "field"}
"""A located problem. components/IssueList.jsx, components/issues.js (formIssues)."""

CHANGE = {"revision", "action", "area", "summary"}
"""One unsaved change. modes/editor/ConfigEditor.jsx (the "Discard changes?" list)."""

COUNTS = {"rooms", "labs", "sections", "courses", "faculty", "patterns", "enabled_patterns"}
"""format.js (describeCounts), modes/generator/ScheduleGenerator.jsx."""

CONFIG_STATE = {
    "status": None,
    "name": None,
    "revision": None,
    "saved_revision": None,
    "dirty": None,
    "changes": [CHANGE],
    "issues": [ISSUE],
    "warnings": [ISSUE],
    "validated_at": None,
    "counts": COUNTS,
}
"""``state.config``. format.js (configStatus), layout/Header.jsx, ConfigEditor.jsx,
ScheduleGenerator.jsx, layout/BrowserSession.jsx, chat/ChatEntry.jsx."""

RUN_SETTINGS = {
    "limit",
    "optimizer_flags",
    "configured_limit",
    "configured_optimizer_flags",
    "limit_overridden",
    "optimizer_flags_overridden",
    "max_limit",
    "limit_capped",
}
"""``state.generation.settings`` once a run has started. ScheduleGenerator.jsx,
modes/viewer/ScheduleViewer.jsx, chat/ChatEntry.jsx (``settings.limit``)."""

GENERATION = {
    "state": None,
    "running": None,
    "found": None,
    "settings": RUN_SETTINGS,
    "config_name": None,
    "config_revision": None,
    "started_at": None,
    "finished_at": None,
    "elapsed_seconds": None,
    "message": None,
    "detail": None,
    "completion_reason": None,
    "cancel_requested": None,
}
"""``state.generation``. ScheduleGenerator.jsx, ScheduleViewer.jsx, ChatEntry.jsx,
state/AppStateProvider.jsx (``running``)."""

STATE_SCHEDULES = {"count", "source", "name", "created_at"}
"""``state.schedules``. ScheduleGenerator.jsx, ScheduleViewer.jsx, BrowserSession.jsx."""

ASSISTANT = {"busy", "entries", "last_entry", "waiting", "available", "reason", "model"}
"""``state.assistant``. chat/useChat.js."""

STATE = {
    "config": CONFIG_STATE,
    "generation": GENERATION,
    "schedules": STATE_SCHEDULES,
    "assistant": ASSISTANT,
}
"""``GET /api/state``, polled by state/AppStateProvider.jsx for every page."""

CONFIGURATION = {"state": CONFIG_STATE, "document": None, "sections": None}
"""``GET /api/config``. ConfigEditor.jsx reads ``document`` and ``sections``;
ScheduleGenerator.jsx reads ``document.limit`` and ``document.optimizer_flags``."""

OPTIONS = {
    "weekdays": None,
    "modalities": None,
    "delivery_modes": None,
    "optimizer_flags": [{"value", "description"}],
    "generation": {"max_schedules"},
}
"""``GET /api/config/options``. ConfigEditor.jsx, cards/SettingsCard.jsx, the edit dialogs
in modes/editor/dialogs/, ScheduleGenerator.jsx."""

REFERENCE = {"area", "index", "label", "field"}
"""An item that refers to the one being deleted. dialogs/DeleteDialog.jsx."""

DELETE_IMPACT = {
    "area": None,
    "index": None,
    "label": None,
    "can_delete": None,
    "can_force": None,
    "blocking": [REFERENCE],
    "cascades": [REFERENCE],
    "problems": [ISSUE],
}
"""``GET /api/config/{area}/{index}/impact``. ConfigEditor.jsx, dialogs/DeleteDialog.jsx."""

MEETING = {
    "course",
    "course_id",
    "section",
    "faculty",
    "room",
    "lab",
    "day",
    "day_number",
    "start",
    "end",
    "start_time",
    "end_time",
    "duration",
    "kind",
    "delivery",
    "reserve_room_during_lab",
    "other",
    "other_label",
    "room_held_for_lab",
}
"""One meeting in a schedule view. modes/viewer/scheduleData.js (toGroups)."""

SCHEDULE_VIEW = {
    "number": None,
    "count": None,
    "group": None,
    "totals": {"sections", "faculty", "rooms", "labs"},
    "groups": [
        {"name": None, "kind": None, "sections": None, "meeting_count": None, "meetings": [MEETING]}
    ],
}
"""``GET /api/schedules/{number}``. modes/viewer/useSchedules.js, ScheduleViewer.jsx,
scheduleData.js."""

ERROR = {"error": {"code": None, "message": None, "issues": [ISSUE]}}
"""Every error reply. api/client.js (ApiError), components/ErrorMessage.jsx."""

UNSAVED_CHANGES = {"error": {"code": None, "message": None, "issues": None, "changes": [CHANGE]}}
"""``409 unsaved_changes`` on New or Load. state/eventHandlers.js (``error.extra.changes``)."""

ENTRY = {"id", "role", "text", "at", "tool", "result", "error", "pending"}
"""One chat entry. chat/ChatEntry.jsx, chat/ChatAssistant.jsx, chat/useChat.js."""

TOOL_RESULT = {"status", "ok", "summary", "error"}
"""A tool entry's ``result``. ChatEntry.jsx (``status``, ``error``)."""

PENDING = {"id", "kind", "prompt", "details", "revision", "state"}
"""A tool entry's ``pending`` action. ChatEntry.jsx (PendingAction)."""

TRANSCRIPT = {"entries": [ENTRY], "busy": None, "available": None, "reason": None, "model": None}
"""``GET /api/chat``. chat/useChat.js."""

FRONTEND_TOOLS = {"edit_configuration", "new_configuration", "generate_schedules"}
"""Tool names chat/ChatAssistant.jsx hardcodes (EDIT_TOOLS, RUN_TOOL)."""

FILENAME = re.compile(r'filename="([^"]+)"')
"""How api/client.js (readSuccess) reads a download's file name."""


def assert_shape(value, shape, where: str = "reply") -> None:
    """Fail unless ``value`` has exactly the fields ``shape`` lists, all the way down."""
    if isinstance(shape, set):
        shape = dict.fromkeys(shape)
    if isinstance(shape, dict):
        assert isinstance(value, dict), f"{where} should be an object, not {value!r}"
        missing = sorted(shape.keys() - value.keys())
        unexpected = sorted(value.keys() - shape.keys())
        assert not missing and not unexpected, (
            f"{where} is missing {missing} and has unexpected {unexpected}. "
            "If you renamed a field, update this shape and the frontend files it names."
        )
        for key, inner in shape.items():
            if inner is not None:
                assert_shape(value[key], inner, f"{where}.{key}")
    elif isinstance(shape, list):
        # An empty list would check nothing, so each test sets up at least one item.
        assert isinstance(value, list) and value, f"{where} should be a non-empty list"
        for position, item in enumerate(value):
            assert_shape(item, shape[0], f"{where}[{position}]")


# ----------------------------------------------------------------- the scenarios


def load(client: TestClient, data: dict, filename: str = "minimal.json") -> None:
    reply = client.post(
        "/api/config/load", json={"filename": filename, "content": json.dumps(data)}
    )
    assert reply.status_code == 200, reply.text


@pytest.fixture
def loaded(client, config_data) -> TestClient:
    load(client, config_data)
    return client


@pytest.fixture
def generated(loaded, controller) -> TestClient:
    """The fixture configuration with one finished run of two schedules."""
    assert loaded.post("/api/generation", json={"limit": 2}).status_code == 202
    controller.job.wait(TIMEOUT)
    return loaded


@pytest.fixture
def ai() -> FakeAIClient:
    return FakeAIClient()


@pytest.fixture
def chat(ai, fake_factory, config_data) -> TestClient:
    """A client whose assistant is the scripted fake AI, with the fixture configuration."""
    controller = AppController(
        generator=partial(generation_steps, scheduler_factory=fake_factory),
        ai_client_factory=lambda: ai,
    )
    client = TestClient(create_app(controller), base_url=BASE_URL)
    load(client, config_data)
    return client


def test_state(client):
    # A new configuration with one edit: it has an unsaved change and is still missing
    # courses and faculty, so `changes` and `issues` both have items.
    client.post("/api/config/new")
    client.post("/api/config/rooms", json={"name": "Room 201", "capacity": 30})

    state = client.get("/api/state").json()

    # No run yet, so there are no run settings; test_state_after_a_run checks them.
    assert_shape(
        state,
        {
            **STATE,
            "config": {**CONFIG_STATE, "warnings": None},
            "generation": {**GENERATION, "settings": None},
        },
    )


def test_state_warnings(client, example_data):
    # Disabling the only pattern that puts Hogg on their mandatory Wednesday warns.
    load(client, example_data, "sample_config.json")
    patterns = client.get("/api/config/patterns").json()["items"]
    index = [refs.pattern_label(pattern) for pattern in patterns].index(
        "4 credits: MON, WED (lab), FRI"
    )
    client.put(
        f"/api/config/patterns/{index}?force=true", json={**patterns[index], "disabled": True}
    )

    config = client.get("/api/state").json()["config"]

    assert_shape(config["warnings"], [ISSUE], "state.config.warnings")


def test_state_after_a_run(generated):
    assert_shape(generated.get("/api/state").json()["generation"], GENERATION, "state.generation")


def test_configuration(loaded):
    loaded.put("/api/config/settings", json={"limit": 2})  # an unsaved change
    configuration = loaded.get("/api/config").json()

    assert_shape(
        configuration,
        {**CONFIGURATION, "state": {**CONFIG_STATE, "issues": None, "warnings": None}},
    )


def test_options(client):
    assert_shape(client.get("/api/config/options").json(), OPTIONS)


def test_delete_impact(loaded):
    # Dr. Smith is the only faculty for CS 101.01 (blocking, and a problem) and one of
    # the faculty for CS 102.01 (a cascade).
    assert_shape(loaded.get("/api/config/faculty/0/impact").json(), DELETE_IMPACT)


@pytest.mark.parametrize("group", ["room", "faculty"])
def test_schedule_view(generated, group):
    assert_shape(generated.get("/api/schedules/1", params={"group": group}).json(), SCHEDULE_VIEW)


def test_configuration_download(loaded):
    reply = loaded.get("/api/config/export")

    assert reply.headers["content-disposition"].startswith("attachment")
    assert FILENAME.search(reply.headers["content-disposition"])
    assert int(reply.headers["x-config-revision"]) >= 0


@pytest.mark.parametrize("fmt", ["json", "csv"])
def test_schedule_download(generated, fmt):
    reply = generated.get("/api/schedules/export", params={"which": "all", "format": fmt})

    assert reply.headers["content-disposition"].startswith("attachment")
    assert FILENAME.search(reply.headers["content-disposition"])


# ---------------------------------------------------------------------- errors


def test_an_error(loaded):
    reply = loaded.post("/api/config/rooms", json={"name": "", "capacity": 3})

    assert reply.status_code == 422
    assert_shape(reply.json(), ERROR)


def test_unsaved_changes(loaded, config_data):
    loaded.put("/api/config/settings", json={"limit": 2})

    reply = loaded.post(
        "/api/config/load", json={"filename": "b.json", "content": json.dumps(config_data)}
    )

    # state/eventHandlers.js asks "Discard changes?" on this code.
    assert reply.json()["error"]["code"] == "unsaved_changes"
    assert_shape(reply.json(), UNSAVED_CHANGES)


def test_no_schedules(loaded):
    reply = loaded.get("/api/schedules/1")

    # modes/viewer/useSchedules.js shows "no schedules yet" instead of an error on this code.
    assert reply.json()["error"]["code"] == "no_schedules"
    assert_shape(reply.json(), {"error": {**ERROR["error"], "issues": None}})


# ------------------------------------------------------------------------ chat


def test_chat_transcript(chat, ai):
    change = {"action": "delete", "area": "faculty", "index": 1}
    ai.script += [calling(tool_call("edit_configuration", changes=[change])), saying("Confirm?")]
    chat.post("/api/chat", json={"message": "Delete Dr. Jones"})

    transcript = chat.get("/api/chat").json()

    assert_shape(transcript, TRANSCRIPT, "chat")
    tool = next(entry for entry in transcript["entries"] if entry["role"] == "tool")
    assert_shape(
        tool, {**dict.fromkeys(ENTRY), "result": TOOL_RESULT, "pending": PENDING}, "tool entry"
    )


def test_a_failed_tool_entry(chat, ai):
    bad_room = {"action": "add", "area": "rooms", "item": {"name": "", "capacity": 1}}
    ai.script += [calling(tool_call("edit_configuration", changes=[bad_room])), saying("No.")]
    chat.post("/api/chat", json={"message": "Add a room"})

    entries = chat.get("/api/chat").json()["entries"]

    tool = next(entry for entry in entries if entry["role"] == "tool")
    error = {"code": None, "message": None, "issues": [ISSUE], "change": None}
    assert_shape(
        tool["result"], {**dict.fromkeys(TOOL_RESULT), "error": error}, "tool entry result"
    )


def test_a_notice_entry(chat, ai):
    ai.script.append(AIError("Couldn't reach OpenAI."))
    chat.post("/api/chat", json={"message": "Hello"})

    entries = chat.get("/api/chat").json()["entries"]

    notice = next(entry for entry in entries if entry["role"] == "notice")
    assert_shape(notice, {**dict.fromkeys(ENTRY), "error": {"code", "message"}}, "notice entry")


def test_the_tools_the_chat_panel_names_exist():
    assert FRONTEND_TOOLS <= set(TOOLS.names())
