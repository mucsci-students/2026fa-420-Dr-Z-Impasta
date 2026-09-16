"""Tests for the ``save`` command.

Author: Foster VanFleet. Ported to the command evaluator.
"""

from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.command import Registry, evaluate
from zimpasta.commands.save_config import (
    BLANK_PATH,
    NO_CONFIG,
    PATH_PROMPT,
    PATH_PROMPT_WITH_DEFAULT,
    SAVED,
    SPECS,
    UNWRITABLE,
)
from zimpasta.session import Session

REGISTRY = Registry(SPECS)


def test_save_full_command_round_trips(config, tmp_path):
    output_file = tmp_path / "saved_config.json"
    session = Session(config=config)
    console = ScriptedConsole()

    evaluate(console, session, f'save "{output_file}"', REGISTRY)

    assert console.prompts == []
    assert SAVED in console.output
    assert session.config_path == output_file.resolve()
    saved = CombinedConfig.model_validate_json(output_file.read_text(encoding="utf-8"))
    assert saved == config


def test_bare_save_prompts_and_then_defaults_to_the_saved_path(config, tmp_path):
    first = tmp_path / "first.json"
    session = Session(config=config)

    console = ScriptedConsole([str(first)])
    evaluate(console, session, "save", REGISTRY)
    assert console.prompts == [PATH_PROMPT]
    assert first.exists()

    console = ScriptedConsole([""])
    evaluate(console, session, "save", REGISTRY)
    assert console.prompts == [PATH_PROMPT_WITH_DEFAULT.format(default=first.resolve())]
    assert SAVED in console.output


def test_bare_save_without_a_default_rejects_a_blank_name(config, tmp_path):
    out = tmp_path / "out.json"
    console = ScriptedConsole(["", str(out)])

    evaluate(console, Session(config=config), "save", REGISTRY)

    assert BLANK_PATH in console.output
    assert out.exists()


def test_save_without_config():
    for line in ("save", "save somewhere.json"):
        console = ScriptedConsole()

        evaluate(console, Session(), line, REGISTRY)

        assert console.output == [NO_CONFIG]
        assert console.prompts == []


def test_save_unwritable_path(config, tmp_path):
    directory = tmp_path / "directory"
    directory.mkdir()
    session = Session(config=config)
    console = ScriptedConsole()

    evaluate(console, session, f'save "{directory}"', REGISTRY)

    assert UNWRITABLE in console.output
    assert session.config_path is None
