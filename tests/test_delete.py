from scheduler import CombinedConfig

from tests.helpers import ScriptedConsole
from zimpasta.commands.delete import (
    CANCELLED,
    DELETED,
    NO_CONFIG,
    NOTHING_TO_DELETE,
    delete,
)
from zimpasta.session import Session


def test_deletes_the_chosen_item(config: CombinedConfig):
    console = ScriptedConsole(["3", "2", "yes"])  # Course -> CS 102 -> confirm

    delete(console, Session(config=config))

    assert DELETED.format(name="CS 102") in console.output
    assert [c.course_id for c in config.config.courses] == ["CS 101"]


def test_cancel_at_category_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["5"])  # Cancel

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_cancel_at_item_menu_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["1", "2"])  # Room -> Cancel

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [r.name for r in config.config.rooms] == ["Room 101"]


def test_declining_confirmation_changes_nothing(config: CombinedConfig):
    console = ScriptedConsole(["3", "1", "no"])  # Course -> CS 101 -> decline

    delete(console, Session(config=config))

    assert console.output[-1] == CANCELLED
    assert [c.course_id for c in config.config.courses] == ["CS 101", "CS 102"]


def test_no_config_loaded_reports_and_asks_nothing():
    console = ScriptedConsole([])

    delete(console, Session(config=None))

    assert console.output == [NO_CONFIG]


def test_delete_that_would_leave_config_invalid_is_rolled_back(config: CombinedConfig):
    # Dr. Smith teaches CS 101; removing her breaks CS 101's faculty reference.
    console = ScriptedConsole(["4", "1", "yes"])  # Faculty -> Dr. Smith -> confirm

    delete(console, Session(config=config))

    assert "Can't delete Dr. Smith" in console.output[-1]
    assert [f.name for f in config.config.faculty] == ["Dr. Smith", "Dr. Jones"]


def test_nothing_to_delete_reports_without_further_prompts(config_data: dict):
    config_data["config"]["labs"] = []
    for course in config_data["config"]["courses"]:
        course["lab"] = []
    config = CombinedConfig.model_validate(config_data)
    console = ScriptedConsole(["2"])  # Lab

    delete(console, Session(config=config))

    assert console.output[-1] == NOTHING_TO_DELETE
