from zimpasta.commands.modify import (
    id_key_choices,
    update_config,
    update_config_config,
    update_config_time_slot_config,
)


def test(config) -> None:
    print(config)


def test_id_key_choices():
    assert id_key_choices("course") == (
        "course_id",
        ("course_id", "credits", "capacity", "room", "lab", "conflicts", "faculty"),
    )

    assert id_key_choices("pizza") == ("", ())

    assert id_key_choices(4) == ("", ())


def test_update_config(config, config_file):
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
