"""Change notifications from the workspace and the schedule set."""

import json
import logging

import pytest

from zimpasta.model.observable import Subject
from zimpasta.model.schedules import InvalidScheduleFile, ScheduleSet
from zimpasta.model.workspace import ConfigWorkspace, EditRejected, InvalidFile

ROOM = {"name": "Room 201", "capacity": 30}


class Counter:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


@pytest.fixture
def workspace(config_data) -> ConfigWorkspace:
    ws = ConfigWorkspace()
    ws.load_text(json.dumps(config_data), filename="biology.json")
    return ws


def test_observers_are_called_until_they_unsubscribe():
    subject, counter = Subject(), Counter()
    unsubscribe = subject.subscribe(counter)

    subject._notify()
    unsubscribe()
    unsubscribe()  # twice is harmless
    subject._notify()

    assert counter.calls == 1


def test_a_failing_observer_is_logged_and_the_others_still_run(caplog):
    subject, counter = Subject(), Counter()

    def broken() -> None:
        raise RuntimeError("boom")

    subject.subscribe(broken)
    subject.subscribe(counter)
    with caplog.at_level(logging.ERROR, logger="zimpasta.model"):
        subject._notify()

    assert counter.calls == 1
    assert "observer of Subject failed" in caplog.text


def test_the_workspace_announces_edits_loads_and_saves(workspace, config_data):
    counter = Counter()
    workspace.subscribe(counter)

    workspace.add("rooms", ROOM)
    with pytest.raises(EditRejected):
        workspace.update_settings({"limit": -1})
    workspace.mark_saved(workspace.revision, "biology.json")
    workspace.new(discard_changes=True)
    workspace.load_text(json.dumps(config_data), filename="b.json")

    assert counter.calls == 4  # the rejected edit isn't announced


def test_a_transaction_is_announced_once_and_only_if_it_succeeds(workspace):
    counter = Counter()
    workspace.subscribe(counter)

    with workspace.transaction():
        workspace.add("rooms", ROOM)
        with workspace.transaction():
            workspace.update_settings({"limit": 5})
    assert counter.calls == 1

    with pytest.raises(EditRejected):
        with workspace.transaction():
            workspace.update_settings({"limit": 6})
            workspace.update_settings({"limit": -1})
    assert counter.calls == 1

    workspace.update_settings({"limit": 7})
    assert counter.calls == 2


def test_record_and_restore_bring_back_unsaved_changes(workspace):
    workspace.add("rooms", ROOM)
    record = workspace.record()
    counter = Counter()
    workspace.subscribe(counter)

    workspace.close()
    assert workspace.status.value == "none" and workspace.document() is None

    workspace.restore(record)

    assert counter.calls == 0
    assert workspace.document() == record["document"]
    assert workspace.name == "biology.json"
    assert workspace.dirty and [c.summary for c in workspace.changes] == ["Added room Room 201"]
    workspace.remove("rooms", 1)  # back to the saved document: no longer dirty
    assert not workspace.dirty


def test_restoring_nothing_closes_and_an_unacceptable_document_is_refused(workspace):
    document = workspace.document()

    with pytest.raises(InvalidFile):
        workspace.restore({"document": {"config": "not a configuration"}})
    assert workspace.document() == document

    workspace.restore({})
    assert workspace.status.value == "none"


def test_schedules_announce_only_complete_sets(real_schedules):
    schedules, counter = ScheduleSet(), Counter()
    schedules.subscribe(counter)

    schedules.start_generated(real_schedules[0], limit=2, optimizer_flags=[])
    schedules.add_generated(real_schedules[1])
    assert counter.calls == 0

    schedules.clear()
    assert counter.calls == 1


def test_schedule_records_round_trip_and_bad_ones_are_refused(real_schedules):
    schedules = ScheduleSet()
    schedules.start_generated(real_schedules[0], limit=2, optimizer_flags=["pack_rooms"])
    record = schedules.record()

    other = ScheduleSet()
    other.restore(record)

    assert other.schedules() == schedules.schedules()
    assert other.summary()["optimizer_flags"] == ["pack_rooms"]
    assert other.source == "generated"
    with pytest.raises(InvalidScheduleFile):
        other.restore({"schedules": [[{"course": "X"}]]})
    assert other.count == 1

    other.restore(None)
    assert other.count == 0 and other.summary()["created_at"] is None
