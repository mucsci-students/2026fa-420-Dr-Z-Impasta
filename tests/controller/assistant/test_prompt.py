"""The base prompt and the state summary sent with each request."""

from zimpasta.controller import AppController
from zimpasta.controller.assistant.prompt import BASE_PROMPT, instructions, state_summary
from zimpasta.controller.assistant.tools import TOOLS


def test_the_base_prompt_describes_every_registered_tool():
    for name in TOOLS.names():
        assert f"- {name}:" in BASE_PROMPT


def test_the_summary_names_items_by_index_and_says_whether_saved(app):
    summary = state_summary(app)

    assert "Configuration: minimal.json (valid, saved)." in summary
    assert "Rooms: [0] Room 101" in summary
    assert "Faculty: [0] Dr. Smith, [1] Dr. Jones" in summary
    assert "Courses: [0] CS 101.01, [1] CS 102.01" in summary
    assert "Settings: limit 3" in summary
    assert "Generation: idle. Schedules in the viewer: 0." in summary

    app.update_settings({"limit": 4})
    assert "(valid, 1 unsaved changes)" in state_summary(app)


def test_the_summary_for_nothing_open_and_for_an_incomplete_configuration():
    app = AppController(ai_client_factory=None)
    assert "No configuration is open" in state_summary(app)

    app.new_configuration()
    summary = state_summary(app)
    assert "(incomplete, saved)" in summary
    assert "Missing before it is valid:" in summary
    assert "Rooms: none" in summary


def test_instructions_are_the_prompt_then_the_state(app):
    text = instructions(app)

    assert text.startswith(BASE_PROMPT)
    assert text.endswith(state_summary(app))
