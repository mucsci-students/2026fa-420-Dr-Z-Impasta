"""The browser version's entry point, run natively: the same calls the Web Worker makes."""

import importlib.metadata
import json

import anyio
import anyio.to_thread
import pytest

from tests.helpers import load_sample_config_data
from zimpasta import browser


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def inline(monkeypatch):
    """Run endpoints inline as on Pyodide, restoring anyio's thread pool afterwards."""
    monkeypatch.setattr(anyio.to_thread, "run_sync", browser.run_inline)


@pytest.fixture
def app(inline):
    return browser.create_browser_app()


async def request(app, method, url, body=None):
    reply = await browser.call(
        app,
        method,
        url,
        headers=[["Accept", "application/json"], ["Content-Type", "application/json"]],
        body="" if body is None else json.dumps(body),
    )
    return reply["status"], reply


async def load_fixture(app, **changes):
    content = json.dumps({**load_sample_config_data(), **changes})
    status, _ = await request(
        app, "POST", "/api/config/load", {"filename": "minimal.json", "content": content}
    )
    assert status == 200


def test_pins_match_the_locked_versions():
    for requirement in browser.REQUIREMENTS + browser.WITHOUT_DEPENDENCIES:
        name, version = requirement.split("==")
        assert importlib.metadata.version(name) == version, requirement


def test_importing_the_module_loads_nothing_else():
    source = open(browser.__file__, encoding="utf-8").read()
    top_level = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert top_level == [
        "import asyncio",
        "import json",
        "from typing import Any",
        "from urllib.parse import unquote",
    ]


@pytest.mark.anyio
async def test_requests_reach_the_same_api(app):
    status, reply = await request(app, "GET", "/api/state")
    assert status == 200
    assert json.loads(reply["body"])["config"]["status"] == "none"

    status, reply = await request(app, "GET", "/api/config/options")
    assert json.loads(reply["body"])["generation"] == {"max_schedules": browser.MAX_SCHEDULES}

    status, reply = await request(app, "GET", "/api/config/rooms")
    assert status == 409
    assert json.loads(reply["body"])["error"]["code"] == "no_configuration"


@pytest.mark.anyio
async def test_generation_runs_on_the_event_loop_and_is_capped(app):
    await load_fixture(app, limit=50)

    status, reply = await request(app, "POST", "/api/generation", {"limit": 6})
    assert status == 422
    assert json.loads(reply["body"])["error"]["issues"][0]["code"] == "limit_above_maximum"

    status, reply = await request(app, "POST", "/api/generation", {})
    assert status == 202
    started = json.loads(reply["body"])
    assert started["running"] and started["settings"]["limit_capped"]
    assert started["settings"]["limit"] == browser.MAX_SCHEDULES

    with anyio.fail_after(60):
        while True:
            await anyio.sleep(0.02)
            _, reply = await request(app, "GET", "/api/generation")
            if not json.loads(reply["body"])["running"]:
                break
    assert json.loads(reply["body"])["state"] == "succeeded"

    status, reply = await request(app, "GET", "/api/schedules/export?format=json&which=all")
    assert status == 200
    headers = dict(reply["headers"])
    assert headers["content-disposition"].startswith("attachment")
    assert json.loads(reply["body"])


@pytest.mark.anyio
async def test_handle_speaks_json_after_start(monkeypatch):
    monkeypatch.setattr(anyio.to_thread, "run_sync", anyio.to_thread.run_sync)  # restored after
    monkeypatch.setattr(browser, "_app", None)
    browser.start()

    reply = json.loads(
        await browser.handle(json.dumps({"method": "GET", "url": "/api/state", "headers": []}))
    )

    assert reply["status"] == 200
    assert ["content-type", "application/json"] in reply["headers"]
    assert json.loads(reply["body"])["generation"]["state"] == "idle"
