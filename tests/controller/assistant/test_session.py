"""The chat loop: requests, tool calls, truthful outcomes, failures, and pending actions."""

import json

import pytest

from tests.helpers import calling, saying, tool_call
from zimpasta.controller import AppController
from zimpasta.controller.assistant import (
    AIError,
    AINotConfigured,
    ChatBusy,
    ChatError,
    PendingNotFound,
    client_from_environment,
)
from zimpasta.controller.assistant.prompt import BASE_PROMPT
from zimpasta.controller.assistant.session import MAX_ROUNDS

ADD_ROOM = {"action": "add", "area": "rooms", "item": {"name": "Room 201", "capacity": 30}}
DELETE_JONES = {"action": "delete", "area": "faculty", "index": 1}


def roles(reply: dict) -> list[str]:
    return [entry["role"] for entry in reply["added"]]


def tool_entries(reply: dict) -> list[dict]:
    return [entry for entry in reply["added"] if entry["role"] == "tool"]


def outputs(request: dict) -> list[dict]:
    return [json.loads(item["output"]) for item in request["input"]]


# ------------------------------------------------------------------- requests


def test_a_request_runs_the_tool_and_reports_its_outcome(app, ai):
    ai.script += [calling(tool_call("edit_configuration", changes=[ADD_ROOM])), saying("Added.")]

    reply = app.chat_send("Add Room 201 with 30 seats")

    assert roles(reply) == ["user", "tool", "assistant"]
    [tool] = tool_entries(reply)
    assert tool["tool"] == "edit_configuration"
    assert tool["result"]["ok"] is True and tool["text"] == "Added room Room 201."
    assert [room["name"] for room in app.workspace.items("rooms")][-1] == "Room 201"
    assert reply["state"]["config"]["dirty"] is True
    assert reply["state"]["assistant"]["busy"] is False


def test_the_model_gets_the_prompt_tools_state_and_tool_results(app, ai):
    ai.script += [calling(tool_call("validate_configuration", call_id="c-9")), saying("Valid.")]

    app.chat_send("Is it valid?")

    first, second = ai.requests
    assert first["instructions"].startswith(BASE_PROMPT)
    assert "[0] Room 101" in first["instructions"]
    assert "[1] Dr. Jones" in first["instructions"]
    assert {tool["name"] for tool in first["tools"]} >= {"edit_configuration", "generate_schedules"}
    assert first["input"][-1] == {"role": "user", "content": "Is it valid?"}
    assert first["previous_id"] is None
    assert second["previous_id"] == "reply-1"
    assert second["input"][0]["call_id"] == "c-9"
    assert outputs(second)[0]["status"] == "done" and outputs(second)[0]["valid"] is True


def test_earlier_turns_are_sent_for_follow_ups(app, ai):
    ai.script += [saying("There is one room."), saying("Its name is Room 101.")]

    app.chat_send("How many rooms are there?")
    app.chat_send("What is it called?")

    assert ai.requests[1]["input"] == [
        {"role": "user", "content": "How many rooms are there?"},
        {"role": "assistant", "content": "There is one room."},
        {"role": "user", "content": "What is it called?"},
    ]


def test_outcomes_come_from_the_tool_not_from_the_reply(app, ai):
    bad = {"action": "update", "area": "faculty", "index": 0, "fields": {"minimum_credits": 99}}
    ai.script += [
        calling(tool_call("edit_configuration", changes=[bad])),
        saying("Done! Dr. Smith now needs 99 credits."),
    ]
    before = app.workspace.document()

    reply = app.chat_send("Make Dr. Smith teach at least 99 credits")

    [tool] = tool_entries(reply)
    assert tool["result"]["ok"] is False
    assert tool["result"]["error"]["code"] == "edit_rejected"
    assert outputs(ai.requests[1])[0]["status"] == "failed"
    assert app.workspace.document() == before


def test_an_unsupported_tool_call_is_reported_back_to_the_model(app, ai):
    ai.script += [calling(tool_call("delete_everything")), saying("I can't do that.")]

    reply = app.chat_send("Wipe the disk")

    [tool] = tool_entries(reply)
    assert tool["result"]["error"]["code"] == "unknown_tool"
    assert outputs(ai.requests[1])[0]["error"]["code"] == "unknown_tool"


def test_a_question_without_tools_is_just_answered(app, ai):
    ai.script.append(saying("I can only help with the scheduler configuration."))

    reply = app.chat_send("What's the weather?")

    assert roles(reply) == ["user", "assistant"]
    assert len(ai.requests) == 1


def test_a_request_stops_after_the_round_limit(app, ai):
    ai.script += [calling(tool_call("generation_status")) for _ in range(MAX_ROUNDS)]

    reply = app.chat_send("Keep checking")

    assert len(ai.requests) == MAX_ROUNDS
    assert reply["added"][-1]["error"]["code"] == "too_many_steps"


@pytest.mark.parametrize("message", ["", "   ", "x" * 4001])
def test_empty_or_huge_messages_are_refused_without_calling_the_api(app, ai, message):
    with pytest.raises(ChatError):
        app.chat_send(message)

    assert ai.requests == []
    assert app.chat()["entries"] == []


# ------------------------------------------------------------------- failures


def test_a_missing_key_is_explained_and_nothing_is_recorded(config_data):
    app = AppController(ai_client_factory=lambda: client_from_environment({}))

    assert app.chat()["available"] is False
    assert "OPENAI_API_KEY" in app.chat()["reason"]
    assert app.state()["assistant"]["available"] is False
    with pytest.raises(AINotConfigured, match="OPENAI_API_KEY"):
        app.chat_send("Add a room")
    assert app.chat()["entries"] == []


def test_an_api_failure_changes_nothing_and_says_so(app, ai):
    ai.script.append(AIError("Couldn't reach OpenAI."))
    before = app.workspace.document()

    reply = app.chat_send("Add a room")

    assert roles(reply) == ["user", "notice"]
    notice = reply["added"][-1]
    assert notice["error"]["code"] == "ai_unavailable"
    assert notice["text"] == "Couldn't reach OpenAI. Nothing was changed."
    assert app.workspace.document() == before
    assert reply["state"]["assistant"]["busy"] is False


def test_a_failure_after_a_tool_ran_reports_what_did_happen(app, ai):
    ai.script += [
        calling(tool_call("edit_configuration", changes=[ADD_ROOM])),
        AIError("OpenAI didn't answer in time."),
    ]

    reply = app.chat_send("Add Room 201")

    assert roles(reply) == ["user", "tool", "notice"]
    assert "did run" in reply["added"][-1]["text"]
    assert "Room 201" in [room["name"] for room in app.workspace.items("rooms")]


def test_a_second_message_while_one_is_running_is_refused(app, ai):
    caught = []

    def meanwhile(request):
        with pytest.raises(ChatBusy) as busy:
            app.chat_send("Again!")
        caught.append(busy.value)
        assert app.state()["assistant"]["busy"] is True
        return saying("Done.")

    ai.script.append(meanwhile)

    app.chat_send("First")

    assert caught and caught[0].code == "chat_busy"
    assert app.state()["assistant"]["busy"] is False


def test_the_browser_version_has_no_assistant():
    app = AppController(ai_client_factory=None, ai_unavailable_reason="Not in the browser.")

    assert app.chat()["available"] is False and app.chat()["reason"] == "Not in the browser."
    with pytest.raises(AINotConfigured, match="Not in the browser"):
        app.chat_send("Hello")


# -------------------------------------------------------------- confirmations


def ask_to_delete_jones(app, ai) -> dict:
    ai.script += [
        calling(tool_call("edit_configuration", changes=[DELETE_JONES])),
        saying("Please confirm the deletion."),
    ]
    reply = app.chat_send("Delete Dr. Jones")
    [tool] = tool_entries(reply)
    return tool["pending"]


def test_a_deletion_waits_until_the_user_confirms(app, ai):
    pending = ask_to_delete_jones(app, ai)

    assert pending["kind"] == "confirm" and pending["state"] == "waiting"
    assert len(app.workspace.items("faculty")) == 2
    assert app.state()["assistant"]["waiting"] == 1

    reply = app.chat_answer(pending["id"], "confirm")

    [entry] = reply["added"]
    assert entry["tool"] == "edit_configuration" and entry["result"]["ok"] is True
    assert [person["name"] for person in app.workspace.items("faculty")] == ["Dr. Smith"]
    [asked] = [e for e in app.chat()["entries"] if (e["pending"] or {}).get("id") == pending["id"]]
    assert asked["pending"]["state"] == "confirmed"
    assert len(ai.requests) == 2  # confirming doesn't call the model


def test_a_cancelled_deletion_changes_nothing(app, ai):
    pending = ask_to_delete_jones(app, ai)
    before = app.workspace.document()

    reply = app.chat_answer(pending["id"], "cancel")

    assert reply["added"][0]["text"] == "Cancelled. Nothing was changed."
    assert app.workspace.document() == before
    with pytest.raises(ChatError, match="already cancelled"):
        app.chat_answer(pending["id"], "confirm")


def test_a_confirmation_expires_if_the_configuration_changed(app, ai):
    pending = ask_to_delete_jones(app, ai)
    app.update_settings({"limit": 5})

    reply = app.chat_answer(pending["id"], "confirm")

    assert reply["added"][0]["error"]["code"] == "pending_expired"
    assert len(app.workspace.items("faculty")) == 2


def test_answers_must_fit_the_pending_action(app, ai):
    pending = ask_to_delete_jones(app, ai)

    with pytest.raises(ChatError, match="confirm or cancel"):
        app.chat_answer(pending["id"], "saved")
    with pytest.raises(PendingNotFound):
        app.chat_answer("p999", "confirm")


# ----------------------------------------------------------- save and generate


def test_a_save_is_reported_only_after_the_file_is_saved(app, ai):
    app.update_settings({"limit": 4})
    ai.script += [calling(tool_call("save_configuration")), saying("Click Save to choose where.")]

    reply = app.chat_send("Save the configuration")
    [tool] = tool_entries(reply)
    pending = tool["pending"]
    assert tool["result"]["status"] == "waiting" and pending["kind"] == "save"
    assert app.workspace.dirty

    with pytest.raises(ChatError, match="isn't marked saved"):
        app.chat_answer(pending["id"], "saved", "minimal.json")

    app.mark_configuration_saved(pending["revision"], "minimal.json")
    done = app.chat_answer(pending["id"], "saved", "minimal.json")

    assert done["added"][0]["text"] == "Saved the configuration as minimal.json."
    assert done["state"]["config"]["dirty"] is False


def test_generation_requested_in_chat_fills_the_viewer(app, ai):
    ai.script += [
        calling(tool_call("generate_schedules", limit=2)),
        saying("Generating; watch the progress bar."),
    ]

    reply = app.chat_send("Generate two schedules")

    [tool] = tool_entries(reply)
    assert tool["result"]["ok"] is True
    assert app.job.wait(10).state.value == "succeeded"
    assert app.state()["generation"]["state"] == "succeeded"
    assert app.schedule_summary()["count"] == 2
    assert app.schedule_view(1, "faculty")["groups"]


# ---------------------------------------------------------------- transcript


def test_the_transcript_persists_until_cleared(app, ai):
    ai.script.append(saying("Hello."))
    app.chat_send("Hi")

    transcript = app.chat()
    assert [entry["text"] for entry in transcript["entries"]] == ["Hi", "Hello."]
    assert transcript["available"] is True and transcript["model"] == "fake-model"
    assert app.state()["assistant"]["entries"] == 2

    app.chat_clear()

    assert app.chat()["entries"] == []
