"""Fixtures available to every test module."""

import json
import shutil
from pathlib import Path

import pytest
from scheduler import CombinedConfig

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

SAMPLE_CONFIG = EXAMPLES / "sample_config.json"
"""A minimal two-course configuration; the fixture most tests pin their assertions to."""

EXAMPLE_CONFIG = EXAMPLES / "example.json"
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
