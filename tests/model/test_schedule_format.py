"""Days and times as every view of a schedule writes them (model.schedule_format)."""

import pytest

from zimpasta.model.schedule_format import DAY_NAMES, clock_text


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, "00:00"), (5, "00:05"), (60, "01:00"), (495, "08:15"), (1439, "23:59")],
)
def test_clock_text(minutes, expected):
    assert clock_text(minutes) == expected


def test_day_names():
    assert DAY_NAMES == {1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI"}
