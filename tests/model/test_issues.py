import copy

import pytest
from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.model.issues import issues_from_error, locate


def errors_for(document: dict):
    with pytest.raises(ValidationError) as caught:
        CombinedConfig.model_validate(document)
    return issues_from_error(caught.value)


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (("config", "faculty", 0, "minimum_credits"), ("faculty", 0, "minimum_credits")),
        (("config", "courses", 3, "room"), ("courses", 3, "room")),
        (("config", "rooms"), ("rooms", None, None)),
        (
            ("time_slot_config", "classes", 2, "meetings", 0, "duration"),
            ("patterns", 2, "meetings.0.duration"),
        ),
        (
            ("time_slot_config", "times", "TUE", 0, "start"),
            ("time_slots", None, "times.TUE.0.start"),
        ),
        (("time_slot_config", "max_time_gap"), ("time_slots", None, "max_time_gap")),
        (("limit",), ("settings", None, "limit")),
        (("optimizer_flags", 1), ("settings", None, "optimizer_flags")),
        (("config",), (None, None, "config")),
        ((), (None, None, None)),
    ],
)
def test_locate(location, expected):
    assert locate(location) == expected


def test_field_error_is_located_on_the_item(config_data):
    document = copy.deepcopy(config_data)
    document["config"]["faculty"][0]["minimum_credits"] = 99

    [problem] = errors_for(document)

    assert (problem.area, problem.index, problem.field) == ("faculty", 0, "minimum_credits")
    assert problem.code == "faculty_minimum_exceeds_maximum_credits"
    assert "cannot be greater than" in problem.message
    assert not problem.message.startswith("Value error")
    assert problem.to_dict()["path"] == "config.faculty.0.minimum_credits"


def test_empty_required_lists_read_as_missing_items(config_data):
    document = copy.deepcopy(config_data)
    for key in ("rooms", "labs", "courses", "faculty"):
        document["config"][key] = []

    issues = errors_for(document)

    assert [problem.area for problem in issues] == ["rooms", "courses", "faculty"]
    assert all(problem.is_missing_required_item for problem in issues)
    assert issues[0].message == "Add at least one room."


def test_other_errors_are_not_missing_items(config_data):
    document = copy.deepcopy(config_data)
    document["limit"] = 0

    [problem] = errors_for(document)

    assert problem.area == "settings"
    assert not problem.is_missing_required_item
