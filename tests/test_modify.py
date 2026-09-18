from tests.helpers import ScriptedConsole
from zimpasta.command import Registry, evaluate
from zimpasta.commands.modify import (
    MODIFY_SPECS,
    UPDATE_SUCCESS,
    id_key_choices,
    update_config,
    update_config_config,
    update_config_time_slot_config,
)
from zimpasta.session import Session


# method author: Stefan Ventura
def run(console: ScriptedConsole, session: Session, line: str) -> None:
    evaluate(console, session, line, Registry(MODIFY_SPECS))


def test_id_key_choices():
    assert id_key_choices("course") == (
        "course_id",
        ("course_id", "credits", "capacity", "room", "lab", "conflicts", "faculty"),
    )

    assert id_key_choices("pizza") == ("", ())

    assert id_key_choices(4) == ("", ())


def test_update_config(config, config_file):

    assert (
        update_config(
            "optimizer_flag", "faculty_lab", "faculty_labs", " ", " ", config, config_file
        )
        != []
    )
    assert (
        update_config("time_slot", "times", "THU: start: 08:00", "spacing", 90, config, config_file)
        != []
    )


def test_upate_config_time_slot_config(config, config_file):

    assert update_config_config("lab", "name", "Linux", "capacity", "30", config, config_file) != []
    assert (
        update_config_config("course", "course_id", "CMSC 140", "room", "135", config, config_file)
        != []
    )
    assert (
        update_config_config(
            "faculty", "name", "Zoppetti", "times", "MON: 10:00-12:00", config, config_file
        )
        != []
    )


def test_update_config_config(config, config_file):

    assert (
        update_config_time_slot_config(
            "class", "credits: 4, MWF, lab: WED", " ", "FRI", "duration: 40", config, config_file
        )
        != []
    )
    assert (
        update_config_time_slot_config(
            "class", "credits: 3, TR", " ", "THU", "day: MON", config, config_file
        )
        != []
    )


def test_console(config, config_file):

    console = ScriptedConsole(["yes"])
    run(
        console,
        Session(config=config, config_path=config_file),
        "modify faculty name Wertz maximum_credits 6",
    )
    assert UPDATE_SUCCESS.format(kind="faculty") in console.output

    # run(console, Session(config=config, config_path=config_file),
    # "modify class \"credits: 3, TR\" null THU \"day: MON\"")
    # assert UPDATE_SUCCESS.format(kind="class") in console.output

    run(
        console,
        Session(config=config, config_path=config_file),
        "modify optimizer_flag same_room same_rooms null null",
    )
    assert UPDATE_SUCCESS.format(kind="optimizer_flag") in console.output
