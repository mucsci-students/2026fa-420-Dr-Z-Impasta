"""Tests for the ``load`` command.

Author: Foster VanFleet. Ported to the command evaluator.
"""

import pytest

from tests.helpers import ScriptedConsole
from zimpasta.command import CommandError, Registry, evaluate
from zimpasta.commands.load_config import (
    FILE_NOT_FOUND,
    INVALID,
    LOADED,
    PATH_PROMPT,
    SPECS,
    UNREADABLE,
)
from zimpasta.session import Session

REGISTRY = Registry(SPECS)


def test_load_valid_config_as_a_full_command(config_file):
    console = ScriptedConsole()
    session = Session()

    evaluate(console, session, f'load "{config_file}"', REGISTRY)

    assert session.config is not None
    assert session.config_path == config_file.resolve()
    assert LOADED in console.output
    assert console.prompts == []


def test_bare_load_prompts_until_a_file_loads(config_file):
    console = ScriptedConsole(["does_not_exist.json", str(config_file)])
    session = Session()

    evaluate(console, session, "load", REGISTRY)

    assert console.prompts == [PATH_PROMPT] * 2
    assert FILE_NOT_FOUND in console.output
    assert LOADED in console.output
    assert any(line.startswith("Running: load ") for line in console.output)
    assert session.config_path == config_file.resolve()


def test_load_invalid_json_then_valid_replaces_only_on_success(config_file, config):
    invalid_file = config_file.parent / "invalid.json"
    invalid_file.write_text("{ invalid json", encoding="utf-8")
    session = Session(config=config)
    original = session.config
    console = ScriptedConsole([str(invalid_file), str(config_file)])

    evaluate(console, session, "load", REGISTRY)

    assert INVALID in console.output
    assert session.config is not original
    assert session.config_path == config_file.resolve()


def test_load_invalid_schema_then_valid(config_file, config):
    invalid_file = config_file.parent / "invalid_schema.json"
    invalid_file.write_text('{"config": {}}', encoding="utf-8")
    session = Session(config=config)
    console = ScriptedConsole([str(invalid_file), str(config_file)])

    evaluate(console, session, "load", REGISTRY)

    assert INVALID in console.output
    assert session.config_path == config_file.resolve()


def test_full_command_failures_are_command_errors_and_keep_the_session(tmp_path, config):
    session = Session(config=config)
    original = session.config
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(CommandError, match=FILE_NOT_FOUND):
        evaluate(ScriptedConsole(), session, f'load "{tmp_path / "missing.json"}"', REGISTRY)
    with pytest.raises(CommandError, match=INVALID):
        evaluate(ScriptedConsole(), session, f'load "{bad_json}"', REGISTRY)
    with pytest.raises(CommandError, match=UNREADABLE):
        evaluate(ScriptedConsole(), session, f'load "{tmp_path}"', REGISTRY)

    assert session.config is original
    assert session.config_path is None
