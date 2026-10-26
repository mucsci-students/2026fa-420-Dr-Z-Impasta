"""A live smoke test against OpenAI: one real, bounded request that edits the configuration.

Deselected by default (see ``addopts`` in pyproject.toml) so routine runs never use the
API. Run it on purpose with ``uv run pytest -m live`` and OPENAI_API_KEY set; without the
key it is skipped. In GitHub Actions it runs only from the manual "AI live test" workflow.
"""

import json
import os

import pytest

from zimpasta.controller import AppController

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY", "").strip(),
        reason="OPENAI_API_KEY is not set, so the live OpenAI test is skipped.",
    ),
]


def test_a_real_request_edits_the_configuration_through_a_tool(config_data):
    app = AppController()
    app.load_configuration("minimal.json", json.dumps(config_data))

    reply = app.chat_send("Add a room named Room 201 with a capacity of 30.")

    tools = [entry for entry in reply["added"] if entry["role"] == "tool"]
    assert any(entry["tool"] == "edit_configuration" and entry["result"]["ok"] for entry in tools)
    assert "Room 201" in [room["name"] for room in app.workspace.items("rooms")]
    assert reply["added"][-1]["role"] == "assistant"
