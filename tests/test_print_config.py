"""Test printing scheduler configurations in human-readable form.

Author: Foster VanFleet
Date: September 16th, 2026
"""
from tests.helpers import ScriptedConsole
from zimpasta.commands.print_config import print_config
from zimpasta.session import Session


def test_print_config_shows_configuration_information(config):
    console = ScriptedConsole()
    session = Session(config=config)

    print_config(console, session)

    assert "Rooms" in console.text
    assert "Room 101" in console.text
    assert "Capacity: 40" in console.text

    assert "Labs" in console.text
    assert "Lab 101" in console.text
    assert "Capacity: 24" in console.text

    assert "Courses" in console.text
    assert "CS 101" in console.text
    assert "CS 102" in console.text

    assert "Faculty" in console.text
    assert "Dr. Smith" in console.text
    assert "Dr. Jones" in console.text


def test_print_config_is_human_readable(config):
    console = ScriptedConsole()
    session = Session(config=config)

    print_config(console, session)

    assert "{" not in console.text
    assert "}" not in console.text
    assert '"rooms"' not in console.text
    assert '"courses"' not in console.text
    assert '"faculty"' not in console.text


def test_print_config_without_configuration():
    console = ScriptedConsole()
    session = Session()

    print_config(console, session)

    assert console.output == ["No configuration is loaded."]
def test_print_config_shows_time_slot_configuration(config):
    console = ScriptedConsole()
    session = Session(config=config)

    print_config(console, session)

    assert "Time Slots" in console.text
    assert "MON: 08:00-17:00 (60 minute spacing)" in console.text
    assert "TUE: 08:00-17:00 (60 minute spacing)" in console.text

    assert "Class Patterns" in console.text
    assert "3 credits" in console.text
    assert "MON, 150 minutes" in console.text
    assert "WED, 75 minutes, lab" in console.text

    assert "Maximum time gap: 30 minutes" in console.text
    assert "Minimum time overlap: 45 minutes" in console.text
def test_print_config_shows_scheduler_options(config):
    console = ScriptedConsole()
    session = Session(config=config)

    print_config(console, session)

    assert "Schedule Limit: 3" in console.text
    assert "Optimizer Flags: None" in console.text

