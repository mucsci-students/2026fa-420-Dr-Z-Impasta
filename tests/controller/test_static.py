"""Serving the built GUI next to the API."""

import pytest
from fastapi.testclient import TestClient

from tests.controller.conftest import BASE_URL
from zimpasta.gui import create_gui_app


@pytest.fixture
def built(tmp_path):
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>GUI</title>", encoding="utf-8")
    (web / "assets" / "app-1234.js").write_text("console.log('app')", encoding="utf-8")
    (web / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not for the browser", encoding="utf-8")
    return web


def test_index_and_assets_are_served(controller, built):
    client = TestClient(create_gui_app(controller, static_dir=built), base_url=BASE_URL)

    index = client.get("/")
    assert index.status_code == 200
    assert "<title>GUI</title>" in index.text
    assert index.headers["cache-control"] == "no-cache"
    assert client.get("/assets/app-1234.js").text == "console.log('app')"
    assert client.get("/favicon.svg").status_code == 200


def test_gui_routes_get_the_index_so_reload_works(controller, built):
    client = TestClient(create_gui_app(controller, static_dir=built), base_url=BASE_URL)

    for path in ("/editor", "/generator", "/viewer", "/viewer/anything"):
        response = client.get(path)
        assert response.status_code == 200
        assert "<title>GUI</title>" in response.text


def test_api_still_wins_and_unknown_api_paths_are_json(controller, built):
    client = TestClient(create_gui_app(controller, static_dir=built), base_url=BASE_URL)

    assert client.get("/api/state").json()["config"]["status"] == "none"
    missing = client.get("/api/nothing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_files_outside_the_build_are_not_served(controller, built):
    client = TestClient(create_gui_app(controller, static_dir=built), base_url=BASE_URL)

    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = client.get(path)
        assert "not for the browser" not in response.text


def test_missing_build_explains_how_to_build(controller, tmp_path):
    client = TestClient(
        create_gui_app(controller, static_dir=tmp_path / "missing"), base_url=BASE_URL
    )

    page = client.get("/viewer")
    assert page.status_code == 503
    assert "hasn't been built" in page.text
    assert "npm run build" in page.text
    assert client.get("/api/state").status_code == 200
