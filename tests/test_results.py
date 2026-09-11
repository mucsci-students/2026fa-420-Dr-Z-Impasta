from datetime import datetime

import pytest

from zimpasta.generate import REASON_TIMEOUT, GenerationResult
from zimpasta.results import ScheduleStore
from zimpasta.view import format_schedule, summarize


def make_result(schedules, *, limit=None, reason=None):
    return GenerationResult(
        schedules=list(schedules),
        limit=limit or len(schedules),
        optimizer_flags=(),
        completion_reason=reason,
        generated_at=datetime(2026, 9, 11, 14, 30),
    )


def test_store_starts_empty():
    store = ScheduleStore()

    assert store.is_empty()
    assert len(store) == 0
    assert store.schedules == []
    with pytest.raises(LookupError):
        store.get(1)


def test_replace_get_and_clear(real_schedules):
    store = ScheduleStore()
    store.replace(make_result(real_schedules))

    assert len(store) == 2
    assert store.get(1) is real_schedules[0]
    assert store.get(2) is real_schedules[1]
    with pytest.raises(IndexError):
        store.get(0)
    with pytest.raises(IndexError):
        store.get(3)

    store.replace(make_result(real_schedules[:1]))
    assert len(store) == 1

    store.clear()
    assert store.is_empty()


def test_summary_lists_each_schedule(real_schedules):
    text = summarize(make_result(real_schedules, limit=5, reason=REASON_TIMEOUT))

    assert "Generated schedules: 2 (limit 5)" in text
    assert "Optimizer flags: none" in text
    assert "Stopped early: the solver timed out" in text
    assert "  1. 2 course section(s)" in text
    assert "  2. 2 course section(s)" in text


def test_format_schedule_shows_every_assignment(real_schedules):
    text = format_schedule(real_schedules[0], number=1)
    lines = text.splitlines()

    assert lines[0] == "Schedule 1"
    assert lines[1].split() == ["Course", "Faculty", "Room", "Lab", "Meetings"]
    body = "\n".join(lines[3:])
    for instance in real_schedules[0]:
        assert instance.course_str in body
        assert instance.faculty in body
        assert instance.room in body
        for index, meeting in enumerate(instance.times):
            assert str(meeting) in body
            if instance.lab_index == index:
                assert f"{meeting} (lab)" in body
    assert "Lab 101" in body
