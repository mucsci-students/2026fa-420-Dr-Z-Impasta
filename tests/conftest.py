"""Fixtures available to every test module."""

import json
import shutil
import socket
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from functools import partial
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from scheduler import CombinedConfig, Scheduler

from tests.helpers import EXAMPLE_CONFIG, FIXTURE_CONFIG, FakeSchedulerFactory, build_config_data
from zimpasta.controller.static import BUILT_GUI
from zimpasta.model.generate import generate_schedules

pytestmark = pytest.mark.skipif(
    not (BUILT_GUI / "index.html").exists(), reason="Run npm run build in frontend first."
)

RUN_SERVER = ["uv", "run", "zimpasta", "--gui", "--no-browser"]


@pytest.fixture(autouse=True)
def no_real_database(monkeypatch):
    """Tests never touch a real account database: no DATABASE_URL, and the GUI's .env
    loading does nothing. Account tests use an in-memory SQLite store instead."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("zimpasta.gui.load_environment", lambda: None)


@pytest.fixture
def config_data() -> dict:
    """A fresh copy of the small test fixture as plain JSON data; edit it freely."""
    return json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8"))


@pytest.fixture
def config(config_data: dict) -> CombinedConfig:
    """The test fixture, validated by the library."""
    return CombinedConfig.model_validate(config_data)


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A copy of the test fixture file inside the test's temporary directory."""
    path = tmp_path / "config.json"
    shutil.copy(FIXTURE_CONFIG, path)
    return path


@pytest.fixture
def example_data() -> dict:
    """A fresh copy of the realistic configuration as plain JSON data; edit it freely."""
    return json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))


@pytest.fixture
def example(example_data: dict) -> CombinedConfig:
    """The realistic configuration, validated by the library."""
    return CombinedConfig.model_validate(example_data)


@pytest.fixture(scope="session")
def real_schedules() -> list:
    """Two real schedules from one fast solve, reused as canned output everywhere else."""
    config = CombinedConfig.model_validate(build_config_data(limit=2))
    return list(Scheduler(config, solver_timeout_ms=10_000).get_models())


@pytest.fixture
def fake_factory(real_schedules: list) -> FakeSchedulerFactory:
    return FakeSchedulerFactory(real_schedules)


@pytest.fixture
def fake_generator(fake_factory: FakeSchedulerFactory):
    """``generate_schedules`` wired to the fake solver, for command-level tests."""
    return partial(generate_schedules, scheduler_factory=fake_factory)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def loaded_config_page(page: Page, site: str) -> Page:
    """The editor with the example configuration loaded through Load JSON…."""
    page.goto(site)

    page.get_by_role("button", name="Load JSON...").click()
    page.locator('input[type="file"]').set_input_files(EXAMPLE_CONFIG)

    expect(
        page.get_by_role("heading", level=2, name="No configuration loaded", exact=True)
    ).not_to_be_visible(timeout=10000)

    return page


@pytest.fixture
def site() -> Iterator[str]:
    port = free_port()
    url = f"http://127.0.0.1:{port}"

    server = subprocess.Popen([*RUN_SERVER, "--port", str(port)])

    try:
        deadline = time.time() + 30

        while time.time() < deadline:
            if server.poll() is not None:
                raise RuntimeError("Server stopped unexpectedly.")

            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Server failed to start.")

        yield url

    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
