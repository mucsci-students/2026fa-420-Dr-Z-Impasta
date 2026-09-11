"""Fixtures available to every test module."""

import json
import shutil
from pathlib import Path

import pytest
from scheduler import CombinedConfig

SAMPLE_CONFIG = Path(__file__).resolve().parents[1] / "examples" / "sample_config.json"


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
