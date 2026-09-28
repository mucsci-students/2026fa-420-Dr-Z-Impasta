"""Schedule set: generated and imported schedules, JSON/CSV export, room and faculty views."""

import json
from datetime import datetime

import pytest
from scheduler.writers import CSVWriter, JSONWriter

from zimpasta.model.generate import GenerationResult
from zimpasta.model.schedules import (
    InvalidScheduleFile,
    NoSchedules,
    ScheduleError,
    ScheduleNotFound,
    ScheduleSet,
    by_faculty,
    by_room,
    meetings,
)


def generated_set(real_schedules, name="minimal.json") -> ScheduleSet:
    result = GenerationResult(
        schedules=list(real_schedules),
        limit=2,
        optimizer_flags=(),
        completion_reason=None,
        generated_at=datetime(2026, 9, 28, 16, 44),
    )
    schedules = ScheduleSet()
    schedules.replace_generated(result, config_name=name)
    return schedules


def written_by(writer_class, schedules, tmp_path, suffix) -> str:
    path = tmp_path / f"library.{suffix}"
    with writer_class(str(path)) as writer:
        for schedule in schedules:
            writer.add_schedule(schedule)
    return path.read_text(encoding="utf-8")


def online(assignment: dict) -> dict:
    return {
        **assignment,
        "times": [{**time, "delivery": "online"} for time in assignment["times"]],
    }


# ------------------------------------------------------------- generated


def test_generated_schedules_are_kept_in_the_library_json_form(real_schedules):
    schedules = generated_set(real_schedules)

    assert schedules.count == 2
    assert schedules.source == "generated"
    first = schedules.schedule(1)[0]
    assert set(first) >= {"course", "faculty", "times", "reserve_room_during_lab"}
    summary = schedules.summary()
    assert summary["name"] == "minimal.json"
    assert summary["limit"] == 2
    assert summary["schedules"][0] == {
        "number": 1,
        "sections": 2,
        "faculty": len({row["faculty"] for row in schedules.schedule(1)}),
        "rooms": 1,
        "labs": 1,
    }


def test_json_export_is_exactly_what_the_library_writes(real_schedules, tmp_path):
    exported = generated_set(real_schedules).export("all", "json")

    assert exported.content == written_by(JSONWriter, real_schedules, tmp_path, "json")
    assert exported.filename == "minimal-schedules.json"
    assert exported.media_type == "application/json"
    assert exported.count == 2
    exported.content.encode("utf-8")


def test_csv_export_matches_the_library_writer(real_schedules, tmp_path):
    schedules = generated_set(real_schedules)

    everything = schedules.export("all", "csv")
    one = schedules.export(2, "csv")

    assert everything.content == written_by(CSVWriter, real_schedules, tmp_path, "csv")
    assert one.content == written_by(CSVWriter, real_schedules[1:], tmp_path, "csv")
    assert one.filename == "minimal-schedule-2.csv"


def test_one_schedule_exports_as_a_one_element_list_that_loads_back(real_schedules):
    schedules = generated_set(real_schedules)

    exported = schedules.export(2, "json")
    again = ScheduleSet()
    count = again.import_text(exported.content, filename=exported.filename)

    assert count == 1
    assert again.schedule(1) == schedules.schedule(2)


def test_exported_set_loads_back(real_schedules):
    schedules = generated_set(real_schedules)
    exported = schedules.export()

    again = ScheduleSet()
    again.import_text(exported.content, filename="saved.json")

    assert again.schedules() == schedules.schedules()
    assert again.source == "imported"
    assert again.summary()["name"] == "saved.json"


# ---------------------------------------------------------------- import


def test_import_a_single_schedule_file(real_schedules):
    single = json.dumps(generated_set(real_schedules).schedule(1))

    schedules = ScheduleSet()

    assert schedules.import_text(single, filename="one.json") == 1


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ('[[{"course": ', "malformed_json"),
        ('{"course": "CS 101.01"}', "invalid_schedule_file"),
        ("[]", "invalid_schedule_file"),
        ('[[{"course": "X.01", "times": [], "reserve_room_during_lab": true}]]', None),
    ],
)
def test_bad_files_are_rejected_and_current_schedules_kept(real_schedules, text, code):
    schedules = generated_set(real_schedules)
    before = schedules.schedules()

    with pytest.raises(InvalidScheduleFile) as caught:
        schedules.import_text(text, filename="bad.json")

    assert caught.value.code == (code or "invalid_schedule_file")
    assert schedules.schedules() == before
    assert schedules.source == "generated"


def test_import_problems_are_located(real_schedules):
    good = generated_set(real_schedules).schedules()
    good[1][0]["times"][0]["day"] = 9
    good[1][1]["lab_index"] = 7
    del good[0][0]["faculty"]

    with pytest.raises(InvalidScheduleFile) as caught:
        ScheduleSet().import_text(json.dumps(good), filename="bad.json")

    paths = {problem.path for problem in caught.value.issues}
    assert {"0.0.faculty", "1.0.times.0.day", "1.1.lab_index"} <= paths


def test_clear(real_schedules):
    schedules = generated_set(real_schedules)

    schedules.clear()

    assert schedules.count == 0
    assert schedules.summary()["source"] is None
    with pytest.raises(NoSchedules):
        schedules.export()


# ----------------------------------------------------------------- views


def test_navigation_bounds(real_schedules):
    schedules = generated_set(real_schedules)

    assert schedules.view(2)["number"] == 2
    assert schedules.view("1")["number"] == 1
    for bad in (0, 3, "x", True):
        with pytest.raises(ScheduleNotFound):
            schedules.view(bad)
    with pytest.raises(ScheduleError):
        schedules.view(1, group="weekday")
    with pytest.raises(NoSchedules):
        ScheduleSet().view(1)


def test_meetings_spell_out_days_and_clock_times():
    assignment = {
        "course": "CS 102.01",
        "faculty": "Dr. Jones",
        "room": "Room 101",
        "lab": "Lab 101",
        "times": [
            {"day": 1, "start": 900, "duration": 75, "delivery": "in_person"},
            {"day": 3, "start": 900, "duration": 75, "delivery": "in_person"},
        ],
        "lab_index": 1,
        "reserve_room_during_lab": True,
    }

    lecture, lab = meetings(assignment)

    assert (lecture["day"], lecture["start_time"], lecture["end_time"]) == ("MON", "15:00", "16:15")
    assert (lecture["kind"], lab["kind"]) == ("lecture", "lab")
    assert (lab["course_id"], lab["section"]) == ("CS 102", "01")


def test_room_view_includes_rooms_and_labs(real_schedules):
    schedules = generated_set(real_schedules)

    view = schedules.view(1, "room")
    groups = {(group["kind"], group["name"]): group for group in view["groups"]}

    assert list(groups) == [("room", "Room 101"), ("lab", "Lab 101")]
    lab_group = groups[("lab", "Lab 101")]
    assert [meeting["kind"] for meeting in lab_group["meetings"]] == ["lab"]
    assert lab_group["meetings"][0]["other"] == lab_group["meetings"][0]["faculty"]
    room = groups[("room", "Room 101")]
    assert room["sections"] == 2
    held = [meeting for meeting in room["meetings"] if meeting["room_held_for_lab"]]
    assert len(held) == 1 and held[0]["kind"] == "lab"
    days = [(meeting["day_number"], meeting["start"]) for meeting in room["meetings"]]
    assert days == sorted(days)


def test_room_view_without_reserved_room_and_online_meetings(real_schedules):
    schedule = generated_set(real_schedules).schedule(1)
    for assignment in schedule:
        assignment["reserve_room_during_lab"] = False
    schedule[0] = online(schedule[0])

    groups = {(group["kind"], group["name"]): group for group in by_room(schedule)}

    assert ("online", "Online") in groups
    assert all(
        not meeting["room_held_for_lab"] for meeting in groups[("room", "Room 101")]["meetings"]
    )


def test_faculty_view(real_schedules):
    schedule = generated_set(real_schedules).schedule(1)

    groups = by_faculty(schedule)

    names = [group["name"] for group in groups]
    assert names == sorted(names)
    assert all(group["kind"] == "faculty" for group in groups)
    locations = {meeting["other"] for group in groups for meeting in group["meetings"]}
    assert locations == {"Room 101", "Lab 101"}
    assert sum(group["sections"] for group in groups) == 2


def test_export_rejects_unknown_format(real_schedules):
    with pytest.raises(ScheduleError):
        generated_set(real_schedules).export("all", "xml")
