import json
from pathlib import Path

from zimpasta.commands.display_schedules import _clock, _rows

SAMPLE = Path(__file__).parent / "sample_schedules.json"


def test_clock_converts_minutes():
    assert _clock(480) == "08:00"
    assert _clock(840) == "14:00"
    assert _clock(630) == "10:30"


def test_rows_one_per_meeting():
    schedules = json.loads(SAMPLE.read_text())
    rows = _rows(schedules)
    assert len(rows) == 9


def test_row_fields():
    schedules = json.loads(SAMPLE.read_text())
    first = _rows(schedules)[0]
    assert first[0] == "1"
    assert first[1] == "CS 101.01"
    assert first[2] == "Dr. Smith"
    assert first[5] == "MON"
    assert first[6] == "14:00"
    assert first[7] == "16:30"


def test_lab_blank_when_absent():
    schedules = json.loads(SAMPLE.read_text())
    rows = _rows(schedules)
    assert rows[0][4] == ""
    assert rows[1][4] == "Lab 101"
