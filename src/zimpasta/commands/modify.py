"""Modify/update a room, lab, course, faculty member, time slot configuration, class,
or optimizer flag from the loaded configuration.

`modify course course_id "CMSC 140" room "Roddy 140"` runs straight away;
a bare `modify`, or a modify command that is missing fields, will tell the user to insert
the missing fields into the command.

The change is made to the loaded configuration and written straight back to its file;
there is no confirmation.

Any modify command is made up of 6 fields:
    1. the "modify" keyword

    2. a kind (the object you want to modify from (ex. course, room, lab, etc.))

    3. a field_id (the name of the key that uniquely identifies the record you want to access
    within the kind (ex. course_id for course, name for faculty, etc.))

    4. a field (the value of the field_id (ex. "Roddy 136", "Linux"))

    5. a key (the name of the key that you want to modify
    (ex. credits, capacity, maximum_credits, etc.)

    6. a value (the new value you want the key to hold)

Some abnormal cases include:
    1. when the field_id or the key is "times", the field
    or the value will be a string of the following format:
    "DAY: TIME" where DAY can be "MON", "TUE", "WED", "THU",
    or "FRI" and TIME is formatted as HH:MM-HH:MM (ex. 08:00-9:50)

    2. when updating an optimizer flag, the key and value (the last two inputs)
    should be the word 'null'
    3. when updating a class, the field (the fourth input) should be the word 'null'
    4. when updating a class, the field_id is a string of the following format:
    "credits: 3, CLASS_PATTERN" or "credits: 4, CLASS_PATTERN, lab: DAY"
    where CLASS_PATTERN is the meeting days (MWF, MW, TR, etc.)
    and DAY is the day of the week when the lab is held (MON, WED, TUE, THU, or FRI)

an example command:
    modify faculty name Wertz "minimum_credits" 3 changes Prof. Wertz's minimum credits from 0 to 3


"""

import json
from pathlib import Path

from pydantic import TypeAdapter
from scheduler import CombinedConfig, TimeRange, TimeRangeString

from zimpasta.command import CommandError, CommandSpec, Invocation, Positional
from zimpasta.commands.common import NO_CONFIG_TO_EDIT as NO_CONFIG
from zimpasta.console import Console
from zimpasta.session import Session

UPDATE_SUCCESS = "{kind} update has succeeded."
UPDATE_FAILED = "{kind} update has not succeeded."
UI_TO_CONFIG = {
    "course": "courses",
    "room": "rooms",
    "lab": "labs",
    "faculty": "faculty",
    "time_slot": "time_slot_config",
    "class": "classes",
    "optimizer_flag": "optimizer_flags",
}


def modify_handler(console: Console, session: Session, inv: Invocation) -> None:
    """Handler: check the ID and field names, apply the update, and say whether it worked."""

    kind = inv.positionals["kind"]
    field_id = inv.positionals["id"]
    field = inv.positionals["field"]
    key = inv.positionals["key"]
    value = inv.positionals["value"]

    id_choices, key_choices = id_key_choices(kind)

    # When `id_choices` is one string, this is a substring check (see tests/test_modify.py).
    if field_id not in id_choices:
        raise CommandError(f"Unknown {kind} ID: {field_id}. Options are {id_choices}")

    if key not in key_choices:
        raise CommandError(f"Unknown field: {key}. Options are {key_choices}")

    update = UPDATERS.get(kind, update_config_config)
    updated = update(kind, field_id, field, key, value, session.config, session.config_path)
    console.say((UPDATE_SUCCESS if updated else UPDATE_FAILED).format(kind=kind))


def modify_builder(console: Console, session: Session, inv: Invocation) -> Invocation | None:
    """Builds a complete modify-command"""
    if session.config is None:
        console.say(NO_CONFIG)
        return None

    console.say("\nPlease specify a ")

    missing_values = inv.missing_with_choices()

    for val in missing_values:
        console.say("- " + val)
    console.say("\n")

    if not missing_values:
        return inv

    return None


MODIFY_SPECS = (
    CommandSpec(
        "modify",
        None,
        positionals=(
            Positional(
                "kind",
                choices=(
                    "course",
                    "room",
                    "lab",
                    "faculty",
                    "time_slot",
                    "class",
                    "optimizer_flag",
                ),
            ),
            Positional("id"),
            Positional("field"),
            Positional("key"),
            Positional("value"),
        ),
        description="Change one field of an item",
        handler=modify_handler,
        builder=modify_builder,
    ),
)


def id_key_choices(kind: str) -> tuple[str | tuple[str, ...], tuple[str, ...]]:
    """The valid ID names and field names for ``kind``, or ``("", ())`` for an unknown kind."""

    match kind:
        case "course":
            return (
                "course_id",
                ("course_id", "credits", "capacity", "room", "lab", "conflicts", "faculty"),
            )
        case "room":
            return ("name", ("name", "capacity"))
        case "lab":
            return ("name", ("name", "capacity"))
        case "faculty":
            return (
                "name",
                (
                    "name",
                    "maximum_credits",
                    "minimum_credits",
                    "unique_course_limit",
                    "maximum_days",
                    "times",
                    "course_preferences",
                    "room_preferences",
                    "lab_preferences",
                ),
            )
        case "time_slot":
            return ("times", ("start", "spacing", "end"))
        case "class":
            return ("", ("credits", "day", "duration", "lab", "disabled"))
        case "optimizer_flag":
            return (
                (
                    "faculty_course",
                    "faculty_room",
                    "faculty_lab",
                    "same_room",
                    "same_lab",
                    "pack_rooms",
                ),
                ("null",),
            )

    return ("", ())


def _write(config: CombinedConfig, config_path: Path | None) -> None:
    """Write the whole configuration back to the file it was loaded from."""
    with open(str(config_path), "w") as file:
        json.dump(config.model_dump(mode="json"), file, indent=4)


def update_config(
    json_obj: str,
    record_name: str,
    record_val: str,
    key: str,
    value: str,
    config: CombinedConfig | None,
    config_path: Path | None,
) -> bool:
    """Update an optimizer flag or a time block; True if the configuration had any."""

    if config is not None:
        records = getattr(config, UI_TO_CONFIG[json_obj])
        for record in records:
            if json_obj == "optimizer_flag" and record == record_name:
                records[records.index(record)] = value

            elif json_obj == "time_slot":
                day = record_val.split(":", 2)[0]
                start_time = record_val.split(":", 2)[2]
                rec = record[1][day]

                for r in rec:
                    if r.start == start_time.strip():
                        data_type = type(getattr(r, key))
                        setattr(r, key, data_type(value))

            # Only the first record is ever looked at: write the file and stop.
            _write(config, config_path)
            return True

    return False


def update_config_time_slot_config(
    json_obj: str,
    record_name: str,
    record_val: str,
    key: str,
    value: str,
    config: CombinedConfig | None,
    config_path: Path | None,
) -> bool:
    """Update a class pattern; True unless there are no patterns."""

    if config is not None:
        records = getattr(config.time_slot_config, UI_TO_CONFIG[json_obj])
        for record in records:
            if json_obj == "class":
                split = record_name.split(",")
                credit_num = split[0].split(":")[1]
                num_of_days = len(split[1])

                record_credit_num = record.credits
                record_meetings = record.meetings

                if int(credit_num) == record_credit_num:
                    if num_of_days - 1 == len(record_meetings):
                        if int(credit_num) == 4:
                            lab_day = split[2].split(":")[1]
                            for rec in record_meetings:
                                if rec.day == lab_day and rec.lab:
                                    rec = change_class_attr(rec, key, value)
                                    break
                        else:
                            record = change_class_attr(record, key, value)

                # Only the first pattern is ever looked at: write the file and stop.
                _write(config, config_path)
                return record != {}
    return False


def change_class_attr(record, key: str, value: str) -> object:
    """Change one field of the meeting on day ``key``; return that meeting, or {} if none."""

    for rec in record:
        if rec.day == key:
            split = value.split(":")
            split_key = split[0]
            split_value = split[1]

            data_type = type(getattr(rec, split_key))
            setattr(rec, split_key, data_type(split_value))
            return rec
    return {}


def update_config_config(
    json_obj: str,
    record_name: str,
    record_val: str,
    key: str,
    value: str,
    config: CombinedConfig | None,
    config_path: Path | None,
) -> bool:
    """Update a room, lab, course, or faculty member; True if one matched."""

    if config is not None:
        records = getattr(config.config, UI_TO_CONFIG[json_obj])

        for record in records:
            if f"{record_name}={record_val}" in str(
                record
            ) or f"{record_name}='{record_val}'" in str(record):
                # A faculty member's times and preferences are dicts, set one entry at a time.
                if json_obj == "faculty" and key in (
                    "times",
                    "course_preferences",
                    "room_preferences",
                    "lab_preferences",
                ):
                    inner_key = value.split(":", 1)[0]
                    value = value.split(":", 1)[1]
                    nested_obj = getattr(record, key)

                    former_val = nested_obj[inner_key]

                    if key == "times":
                        value = str(
                            TimeRange.from_string(
                                TypeAdapter(TimeRangeString).validate_python(str(value).strip())
                            )
                        )
                    else:
                        data_type = type(former_val)
                        value = data_type(value)

                    nested_obj[inner_key] = value
                else:
                    data_type = type(getattr(record, key))
                    setattr(record, key, data_type(value))

                _write(config, config_path)
                return True
    return False


UPDATERS = {
    "time_slot": update_config,
    "optimizer_flag": update_config,
    "class": update_config_time_slot_config,
}
"""Kinds stored outside ``config.config``; every other kind uses ``update_config_config``."""
