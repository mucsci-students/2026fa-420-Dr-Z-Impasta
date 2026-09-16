"""Fixtures available to every test module."""

import json
import shutil
from functools import partial
from pathlib import Path

import pytest
from scheduler import CombinedConfig, Scheduler

from tests.helpers import SAMPLE_CONFIG, FakeSchedulerFactory, build_config_data
from zimpasta.generate import generate_schedules

EXAMPLE_CONFIG = SAMPLE_CONFIG.parent / "example.json"
"""A realistic department configuration: many courses, several sharing a course id."""


@pytest.fixture
def config_data() -> dict:
    """A fresh copy of the sample configuration as plain JSON data; edit it freely."""
    return json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))


@pytest.fixture
def config(config_data: dict) -> CombinedConfig:
    """The sample configuration, validated by the library."""
    return CombinedConfig.model_validate(config_data)


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A copy of the sample configuration file inside the test's temporary directory."""
    path = tmp_path / "config.json"
    shutil.copy(SAMPLE_CONFIG, path)
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
