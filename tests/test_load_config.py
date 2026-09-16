"""Test loading and validating scheduler configurations.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from pathlib import Path

from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.commands.load_config import load_config
from zimpasta.session import Session


def test_load_valid_config(config_file: Path) -> None:
    console = ScriptedConsole([str(config_file)])
    session = Session()

    load_config(console, session)

    assert session.config is not None
    assert session.config_path == config_file
    assert "Configuration loaded successfully." in console.text


def test_load_missing_file_then_valid_config(config_file: Path) -> None:
    console = ScriptedConsole(["does_not_exist.json", str(config_file)])
    session = Session()

    load_config(console, session)

    assert session.config is not None
    assert session.config_path == config_file
    assert "File not found." in console.text
    assert "Configuration loaded successfully." in console.text


def test_load_invalid_config_does_not_replace_existing(
    config_file: Path,
) -> None:
    invalid_file = config_file.parent / "invalid.json"
    invalid_file.write_text("{ invalid json", encoding="utf-8")

    session = Session()
    session.config = CombinedConfig.model_validate_json(
        config_file.read_text(encoding="utf-8")
    )

    original_config = session.config

    console = ScriptedConsole([str(invalid_file), str(config_file)])

    load_config(console, session)

    assert session.config is not None
    assert session.config is not original_config
    assert session.config_path == config_file
    assert "Invalid configuration file." in console.text


def test_load_invalid_schema_does_not_replace_existing(
    config_file: Path,
) -> None:
    invalid_file = config_file.parent / "invalid_schema.json"
    invalid_file.write_text('{"config": {}}', encoding="utf-8")

    session = Session()
    session.config = CombinedConfig.model_validate_json(
        config_file.read_text(encoding="utf-8")
    )

    original_config = session.config

    console = ScriptedConsole([str(invalid_file), str(config_file)])

    load_config(console, session)

    assert session.config is not None
    assert session.config is not original_config
    assert session.config_path == config_file
    assert "Invalid configuration file." in console.text
