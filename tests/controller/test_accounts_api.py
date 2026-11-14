"""The account and saved-state routes, on an in-memory SQLite store."""

import json
from functools import partial

import pytest
from fastapi.testclient import TestClient

from zimpasta.controller import AppController, create_app
from zimpasta.model.accounts.sql_store import SqlAccountStore, engine_for
from zimpasta.model.generate import generation_steps

BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "correct horse battery"


@pytest.fixture
def store() -> SqlAccountStore:
    return SqlAccountStore(engine_for("sqlite://"))


@pytest.fixture
def app(store, fake_factory, config_data) -> AppController:
    controller = AppController(
        generator=partial(generation_steps, scheduler_factory=fake_factory),
        ai_client_factory=None,
        account_store_factory=lambda: store,
    )
    controller.load_configuration("biology.json", json.dumps(config_data))
    return controller


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(create_app(app), base_url=BASE_URL)


def sign_up(client, username="ada") -> dict:
    reply = client.post("/api/account/signup", json={"username": username, "password": PASSWORD})
    assert reply.status_code == 200, reply.json()
    return reply.json()


def test_the_account_status_before_logging_in(client):
    status = client.get("/api/account").json()

    assert status["available"] is True and status["user"] is None
    assert client.get("/api/state").json()["account"] == status
    assert client.get("/api/states").json()["error"]["code"] == "not_logged_in"


def test_signing_up_logs_in_with_the_open_work_as_the_first_state(client):
    body = sign_up(client)

    account = body["state"]["account"]
    assert account["user"] == {"username": "ada"}
    assert account["state"]["name"] == "My first state"
    assert [state["name"] for state in body["states"]] == ["My first state"]
    assert body["state"]["config"]["name"] == "biology.json"


def test_creating_switching_and_persisting_states(client):
    sign_up(client)
    created = client.post("/api/states", json={"name": "Chemistry"})
    assert created.status_code == 201
    assert created.json()["state"]["config"]["status"] == "none"

    first = next(s for s in created.json()["states"] if s["name"] == "My first state")
    opened = client.post(f"/api/states/{first['id']}/open").json()
    assert opened["state"]["config"]["name"] == "biology.json"
    assert opened["state"]["account"]["state"]["name"] == "My first state"

    client.post("/api/account/logout")
    assert client.get("/api/config").json()["document"] is None

    again = client.post("/api/account/login", json={"username": "ADA", "password": PASSWORD})
    assert again.status_code == 200
    assert again.json()["state"]["account"]["state"]["name"] == "My first state"
    assert client.get("/api/config").json()["state"]["name"] == "biology.json"


def test_renaming_and_deleting_states(client):
    body = sign_up(client)
    first = body["states"][0]["id"]
    chemistry = client.post("/api/states", json={"name": "Chemistry"}).json()

    renamed = client.patch(f"/api/states/{first}", json={"name": "Biology"}).json()
    assert {s["name"] for s in renamed["states"]} == {"Biology", "Chemistry"}

    open_id = chemistry["state"]["account"]["state"]["id"]
    in_use = client.delete(f"/api/states/{open_id}")
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "state_in_use"

    deleted = client.delete(f"/api/states/{first}").json()
    assert [s["name"] for s in deleted["states"]] == ["Chemistry"]
    assert client.delete(f"/api/states/{first}").status_code == 404


@pytest.mark.parametrize(
    ("path", "body", "status", "code"),
    [
        (
            "/api/account/login",
            {"username": "ada", "password": "wrong password"},
            401,
            "invalid_credentials",
        ),
        (
            "/api/account/login",
            {"username": "nobody", "password": PASSWORD},
            401,
            "invalid_credentials",
        ),
        ("/api/account/signup", {"username": "ada", "password": PASSWORD}, 409, "username_taken"),
        (
            "/api/account/signup",
            {"username": "x", "password": PASSWORD},
            400,
            "invalid_account_input",
        ),
        (
            "/api/account/signup",
            {"username": "bob", "password": "short"},
            400,
            "invalid_account_input",
        ),
        ("/api/states", {"name": "My first state"}, 409, "state_name_taken"),
        ("/api/states/999/open", None, 404, "state_not_found"),
    ],
)
def test_account_errors_use_the_usual_shape(client, path, body, status, code):
    sign_up(client)

    reply = client.post(path, json=body) if body is not None else client.post(path)

    assert reply.status_code == status
    assert reply.json()["error"]["code"] == code
    assert PASSWORD not in reply.text and "wrong password" not in reply.text


def test_the_password_is_never_echoed_in_validation_errors(client):
    secret = "hunter2-" * 200  # longer than the route accepts

    reply = client.post("/api/account/signup", json={"username": "ada", "password": secret})

    assert reply.status_code == 400
    assert reply.json()["error"]["details"][0]["location"] == "body.password"
    assert "hunter2" not in reply.text


def test_switching_waits_for_a_running_generation(client, app):
    body = sign_up(client)
    app.job.status = lambda: type("S", (), {"running": True})()

    reply = client.post("/api/states", json={"name": "Chemistry"})

    assert reply.status_code == 409 and reply.json()["error"]["code"] == "generation_running"
    assert [s["name"] for s in body["states"]] == ["My first state"]


def test_without_a_database_accounts_explain_themselves(fake_factory):
    app = AppController(
        generator=partial(generation_steps, scheduler_factory=fake_factory),
        ai_client_factory=None,
    )
    client = TestClient(create_app(app), base_url=BASE_URL)

    status = client.get("/api/account").json()
    assert status["available"] is False and "DATABASE_URL" in status["reason"]

    reply = client.post("/api/account/login", json={"username": "ada", "password": PASSWORD})
    assert reply.status_code == 503
    assert reply.json()["error"]["code"] == "accounts_unavailable"
