"""Test saving scheduler configurations to JSON files.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from pathlib import Path

from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.commands.save_config import save_config
from zimpasta.session import Session


def test_save_config(config: CombinedConfig, tmp_path: Path) -> None:
    output_file = tmp_path / "saved_config.json"

    session = Session(config=config)
    console = ScriptedConsole([str(output_file)])

    save_config(console, session)

    assert output_file.exists()
    assert "Configuration saved successfully." in console.text
    assert session.config_path == output_file

    saved_config = CombinedConfig.model_validate_json(
        output_file.read_text(encoding="utf-8")
    )

    assert saved_config == config


def test_save_without_config() -> None:
    session = Session()
    console = ScriptedConsole()

    save_config(console, session)

    assert console.output == ["No configuration is loaded."]


def test_save_unwritable_path(config: CombinedConfig, tmp_path: Path) -> None:
    session = Session(config=config)

    # A directory cannot be written to as a file.
    output_path = tmp_path / "directory"
    output_path.mkdir()

    console = ScriptedConsole([str(output_path)])

    save_config(console, session)

    assert "Unable to save configuration." in console.text
