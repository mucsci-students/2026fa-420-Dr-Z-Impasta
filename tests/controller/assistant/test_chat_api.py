"""The chat routes under /api/chat, with a scripted AI."""

import json
from functools import partial

import pytest
from fastapi.testclient import TestClient

from tests.helpers import FakeAIClient, calling, saying, tool_call
from zimpasta.controller import AppController, create_app
from zimpasta.controller.assistant import client_from_environment
from zimpasta.model.generate import generation_steps

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(create_app(app), base_url=BASE_URL)


def test_the_transcript_and_availability(client):
    reply = client.get("/api/chat")

    assert reply.status_code == 200
    assert reply.json() == {
        "entries": [],
        "busy": False,
        "available": True,
        "reason": None,
        "model": "fake-model",
    }
    assert client.get("/api/state").json()["assistant"]["available"] is True


def test_sending_a_message_returns_the_new_entries_and_state(client, ai):
    ai.script += [calling(tool_call("validate_configuration")), saying("It's valid.")]

    reply = client.post("/api/chat", json={"message": "Is it valid?"})

    assert reply.status_code == 200
    body = reply.json()
    assert [entry["role"] for entry in body["added"]] == ["user", "tool", "assistant"]
    assert body["state"]["config"]["status"] == "valid"
    assert len(client.get("/api/chat").json()["entries"]) == 3


def test_confirming_through_the_api(client, ai):
    change = {"action": "delete", "area": "faculty", "index": 1}
    ai.script += [calling(tool_call("edit_configuration", changes=[change])), saying("Confirm?")]
    added = client.post("/api/chat", json={"message": "Delete Dr. Jones"}).json()["added"]
    pending = next(entry["pending"] for entry in added if entry["pending"])

    reply = client.post(f"/api/chat/pending/{pending['id']}", json={"answer": "confirm"})

    assert reply.status_code == 200
    assert reply.json()["added"][0]["result"]["ok"] is True
    assert reply.json()["state"]["config"]["counts"]["faculty"] == 1


def test_clearing_the_transcript(client, ai):
    ai.script.append(saying("Hi."))
    client.post("/api/chat", json={"message": "Hello"})

    assert client.delete("/api/chat").status_code == 200
    assert client.get("/api/chat").json()["entries"] == []


@pytest.mark.parametrize(
    ("method", "path", "body", "status", "code"),
    [
        ("post", "/api/chat", {"message": ""}, 400, "bad_request"),
        ("post", "/api/chat", {"message": "   "}, 400, "empty_message"),
        ("post", "/api/chat", {}, 400, "bad_request"),
        ("post", "/api/chat/pending/p404", {"answer": "confirm"}, 404, "not_found"),
        ("post", "/api/chat/pending/p404", {"answer": "maybe"}, 400, "bad_request"),
    ],
)
def test_bad_requests_get_the_usual_error_shape(client, method, path, body, status, code):
    reply = getattr(client, method)(path, json=body)

    assert reply.status_code == status
    assert reply.json()["error"]["code"] == code


def test_a_missing_key_is_a_503_with_instructions(config_data):
    app = AppController(
        generator=partial(generation_steps),
        ai_client_factory=lambda: client_from_environment({}),
    )
    app.load_configuration("minimal.json", json.dumps(config_data))
    client = TestClient(create_app(app), base_url=BASE_URL)

    reply = client.post("/api/chat", json={"message": "Add a room"})

    assert reply.status_code == 503
    assert reply.json()["error"]["code"] == "ai_not_configured"
    assert "OPENAI_API_KEY" in reply.json()["error"]["message"]
    assert client.get("/api/chat").json()["available"] is False


def test_an_api_failure_is_reported_in_the_transcript(client, ai):
    from zimpasta.controller.assistant import AIError

    ai.script.append(AIError("Couldn't reach OpenAI."))

    reply = client.post("/api/chat", json={"message": "Add a room"})

    assert reply.status_code == 200
    assert reply.json()["added"][-1]["error"]["code"] == "ai_unavailable"


def test_fake_ai_used_by_these_tests_is_not_called_unexpectedly():
    with pytest.raises(AssertionError, match="more often than the test scripted"):
        FakeAIClient().respond(instructions="", input=[], tools=[])
