"""The HTTP API: routes, status codes, the error shape, downloads, and local-only rules."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.controller.conftest import BASE_URL
from zimpasta.controller import create_app
from zimpasta.model.generation_job import GenerationBusy

TIMEOUT = 10


@pytest.fixture
def loaded(client, config_data):
    response = client.post(
        "/api/config/load", json={"filename": "minimal.json", "content": json.dumps(config_data)}
    )
    assert response.status_code == 200
    return client


def error(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()["error"]
    assert body["code"] == code
    assert body["message"]
    return body


# ---------------------------------------------------------------- configuration


def test_state_and_configuration(loaded):
    state = loaded.get("/api/state").json()
    assert state["config"]["name"] == "minimal.json"

    config = loaded.get("/api/config").json()
    assert config["document"]["config"]["rooms"][0]["name"] == "Room 101"
    assert config["sections"] == ["CS 101.01", "CS 102.01"]


def test_schema_and_options(client):
    assert "$defs" in client.get("/api/config/schema").json()
    flags = client.get("/api/config/options").json()["optimizer_flags"]
    assert flags[0] == {
        "value": "faculty_course",
        "description": "Optimize faculty course assignments using preferences",
    }


def test_new_with_and_without_a_body(client):
    assert client.post("/api/config/new").json()["state"]["status"] == "incomplete"
    assert client.post("/api/config/new", json={"discard_changes": True}).status_code == 200


def test_load_errors(client, config_data):
    body = error(
        client.post("/api/config/load", json={"filename": "x.json", "content": "{"}),
        400,
        "malformed_json",
    )
    assert "line 1" in body["message"]

    config_data["config"]["faculty"][0]["maximum_credits"] = -1
    body = error(
        client.post(
            "/api/config/load", json={"filename": "x.json", "content": json.dumps(config_data)}
        ),
        422,
        "invalid_configuration",
    )
    assert body["issues"][0]["area"] == "faculty"

    error(client.post("/api/config/load", json={"content": "{}"}), 400, "bad_request")


def test_unsaved_changes_are_listed(loaded, config_data):
    loaded.put("/api/config/settings", json={"limit": 2})

    body = error(
        loaded.post(
            "/api/config/load", json={"filename": "b.json", "content": json.dumps(config_data)}
        ),
        409,
        "unsaved_changes",
    )

    assert body["changes"][0]["summary"] == "Settings: limit 3 → 2"


def test_crud_over_http(loaded):
    added = loaded.post("/api/config/rooms", json={"name": "Room 201", "capacity": 30})
    assert added.status_code == 201
    assert added.json()["index"] == 1
    assert added.json()["change"]["action"] == "added"

    room = loaded.get("/api/config/rooms/1").json()["item"]
    room["capacity"] = 31
    assert loaded.put("/api/config/rooms/1", json=room).json()["change"]["action"] == "edited"

    impact = loaded.get("/api/config/rooms/1/impact").json()
    assert impact["can_delete"] is True
    removed = loaded.delete("/api/config/rooms/1").json()
    assert removed["change"]["action"] == "removed"
    assert len(loaded.get("/api/config/rooms").json()["items"]) == 1

    assert loaded.put("/api/config/time-slots", json={"min_time_overlap": 30}).status_code == 200
    settings = loaded.put("/api/config/settings", json={"optimizer_flags": ["pack_labs"]})
    assert settings.json()["document"]["optimizer_flags"] == ["pack_labs"]


def test_edit_errors(loaded):
    body = error(
        loaded.post("/api/config/rooms", json={"name": "", "capacity": 3}), 422, "edit_rejected"
    )
    assert body["issues"][0]["area"] == "rooms"

    error(loaded.get("/api/config/rooms/9"), 404, "not_found")
    error(loaded.get("/api/config/buildings"), 404, "not_found")
    error(loaded.get("/api/config/rooms/first"), 400, "bad_request")
    error(loaded.post("/api/config/rooms", json=[1, 2]), 400, "bad_request")


def test_blocked_delete_returns_the_impact(loaded):
    body = error(loaded.delete("/api/config/rooms/0"), 409, "delete_blocked")

    assert [ref["label"] for ref in body["impact"]["blocking"]] == ["CS 101.01", "CS 102.01"]


def test_nothing_open(client):
    error(client.get("/api/config/rooms"), 409, "no_configuration")
    error(client.get("/api/config/export"), 409, "no_configuration")


def test_export_and_mark_saved(loaded):
    response = loaded.get("/api/config/export")

    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="minimal.json"'
    revision = int(response.headers["x-config-revision"])
    assert json.loads(response.content.decode("utf-8"))["limit"] == 3

    state = loaded.post("/api/config/saved", json={"revision": revision, "filename": "m2.json"})
    assert state.json()["name"] == "m2.json"


def test_incomplete_configuration_can_not_be_exported(client):
    client.post("/api/config/new")

    body = error(client.get("/api/config/export"), 409, "configuration_incomplete")

    assert len(body["issues"]) == 3


# ------------------------------------------------------------------- generation


def test_generation_flow(loaded, controller):
    started = loaded.post("/api/generation", json={"limit": 1, "optimizer_flags": []})
    assert started.status_code == 202
    controller.job.wait(TIMEOUT)

    status = loaded.get("/api/generation").json()
    assert status["state"] == "succeeded"
    assert status["settings"]["limit"] == 1

    summary = loaded.get("/api/schedules").json()
    assert summary["count"] == 1
    view = loaded.get("/api/schedules/1", params={"group": "faculty"}).json()
    assert view["group"] == "faculty"


def test_generation_errors(loaded, client, controller, monkeypatch):
    body = error(loaded.post("/api/generation", json={"limit": "many"}), 422, "invalid_overrides")
    assert body["issues"][0]["field"] == "limit"

    def busy(*args, **kwargs):
        raise GenerationBusy()

    monkeypatch.setattr(controller.job, "start", busy)
    error(loaded.post("/api/generation"), 409, "generation_running")
    assert loaded.post("/api/generation/cancel").json()["state"] == "idle"


def test_generation_without_valid_configuration(client):
    error(client.post("/api/generation", json={}), 409, "no_configuration")


# -------------------------------------------------------------------- schedules


def test_schedule_endpoints(loaded, controller):
    loaded.post("/api/generation", json={"limit": 2})
    controller.job.wait(TIMEOUT)

    exported = loaded.get("/api/schedules/export", params={"format": "json", "which": "all"})
    assert exported.headers["content-disposition"].endswith('-schedules.json"')
    one = loaded.get("/api/schedules/export", params={"which": "2", "format": "csv"})
    assert one.headers["content-type"] == "text/csv; charset=utf-8"

    imported = loaded.post(
        "/api/schedules/import", json={"filename": "old.json", "content": exported.text}
    )
    assert imported.json()["count"] == 2
    assert loaded.get("/api/schedules/2", params={"group": "room"}).status_code == 200

    error(loaded.get("/api/schedules/3"), 404, "not_found")
    error(loaded.get("/api/schedules/1", params={"group": "day"}), 400, "bad_request")
    error(loaded.get("/api/schedules/export", params={"which": "two"}), 400, "bad_request")
    body = error(
        loaded.post("/api/schedules/import", json={"filename": "b.json", "content": "[[]]x"}),
        400,
        "malformed_json",
    )
    assert loaded.get("/api/schedules").json()["name"] == "old.json"
    assert body["issues"] == []

    assert loaded.delete("/api/schedules").json()["count"] == 0
    error(loaded.get("/api/schedules/export"), 409, "no_schedules")


# ------------------------------------------------------------- local-only rules


def test_requests_for_other_hosts_are_refused(client):
    error(client.get("/api/state", headers={"host": "evil.example"}), 400, "bad_host")
    assert client.get("/api/state", headers={"host": "localhost:8000"}).status_code == 200
    assert client.get("/api/state", headers={"host": "[::1]:8000"}).status_code == 200


def test_cross_site_state_changes_are_refused(client):
    error(
        client.post("/api/config/new", headers={"origin": "https://evil.example"}),
        403,
        "cross_origin",
    )
    error(client.post("/api/config/new", headers={"origin": "null"}), 403, "cross_origin")
    same = client.post("/api/config/new", headers={"origin": BASE_URL})
    assert same.status_code == 200
    assert client.get("/api/state", headers={"origin": "https://evil.example"}).status_code == 200


def test_bodies_must_be_json(client):
    error(
        client.post("/api/config/new", content="x", headers={"content-type": "text/plain"}),
        415,
        "json_required",
    )


def test_unknown_endpoint(client):
    error(client.get("/api/nothing-here"), 404, "not_found")


def test_unexpected_errors_are_friendly(controller, monkeypatch):
    def explode():
        raise RuntimeError("boom")

    monkeypatch.setattr(controller, "state", explode)
    client = TestClient(create_app(controller), base_url=BASE_URL, raise_server_exceptions=False)

    body = error(client.get("/api/state"), 500, "unexpected")

    assert "boom" not in body["message"]
    assert body["reference"] in body["message"]
