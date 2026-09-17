"""Tests for the display schedules command.

This test module verifies that the display command can:

1. Convert minutes into HH:MM time format.
2. Convert JSON schedule data into display rows.
3. Read and parse CSV schedule files.
4. Handle empty and malformed schedule files.
5. Display CSV and JSON schedules.
6. Handle invalid file selections.
7. Handle missing files.
8. Register the display command correctly.

The tests use pytest and a FakeConsole so that user input and
console output can be tested without requiring manual interaction.
"""

import json

import pytest

from zimpasta.commands import display_schedules as mod


class FakeConsole:
    """Fake console used to test user input and output.

    The real Console class interacts with the terminal. This class
    records messages sent to the console and provides predefined
    answers when the program asks the user to choose a file.
    """

    def __init__(self, answers=None):
        """Create a fake console.

        Args:
            answers: Answers that should be returned by ask().
        """
        self.lines = []
        self.prompts = []
        self._answers = list(answers or [])

    def say(self, text):
        """Record text printed by the program."""
        self.lines.append(text)

    def ask(self, prompt):
        """Return the next predefined user answer."""
        self.prompts.append(prompt)

        if not self._answers:
            raise AssertionError(
                "ask() called more times than expected"
            )

        return self._answers.pop(0)

    @property
    def output(self):
        """Return all console output as one string."""
        return "\n".join(self.lines)


def run_display(console):
    """Run the display command using the fake console."""
    mod.display_schedules(
        console,
        session=None,
        invocation=None,
    )


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run a test inside a temporary working directory.

    This prevents the tests from creating or reading files from
    the actual project directory.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ----------------------------------------------------------------------
# _clock tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "minutes, expected",
    [
        (0, "00:00"),
        (5, "00:05"),
        (60, "01:00"),
        (495, "08:15"),
        (1439, "23:59"),
    ],
)
def test_clock(minutes, expected):
    """Test conversion of minutes into HH:MM format."""
    assert mod._clock(minutes) == expected


# ----------------------------------------------------------------------
# _rows tests
# ----------------------------------------------------------------------


def test_rows_builds_one_row_per_meeting():
    """Test that every meeting becomes a separate display row."""
    schedules = [
        [
            {
                "course": "CS101",
                "faculty": "Smith",
                "room": "R1",
                "lab": "L1",
                "times": [
                    {
                        "day": 1,
                        "start": 480,
                        "duration": 50,
                    },
                    {
                        "day": 3,
                        "start": 480,
                        "duration": 50,
                    },
                ],
            }
        ],
        [
            {
                "course": "CS202",
                "faculty": "Jones",
                "times": [
                    {
                        "day": 2,
                        "start": 600,
                        "duration": 75,
                    }
                ],
            }
        ],
    ]

    assert mod._rows(schedules) == [
        [
            "1",
            "CS101",
            "Smith",
            "R1",
            "L1",
            "MON",
            "08:00",
            "08:50",
        ],
        [
            "1",
            "CS101",
            "Smith",
            "R1",
            "L1",
            "WED",
            "08:00",
            "08:50",
        ],
        [
            "2",
            "CS202",
            "Jones",
            "",
            "",
            "TUE",
            "10:00",
            "11:15",
        ],
    ]


def test_rows_multiple_assignments_same_schedule():
    """Test multiple courses within the same schedule."""
    schedules = [
        [
            {
                "course": "CS101",
                "faculty": "Smith",
                "times": [
                    {
                        "day": 1,
                        "start": 480,
                        "duration": 50,
                    }
                ],
            },
            {
                "course": "CS102",
                "faculty": "Jones",
                "times": [
                    {
                        "day": 2,
                        "start": 600,
                        "duration": 75,
                    }
                ],
            },
        ]
    ]

    assert mod._rows(schedules) == [
        [
            "1",
            "CS101",
            "Smith",
            "",
            "",
            "MON",
            "08:00",
            "08:50",
        ],
        [
            "1",
            "CS102",
            "Jones",
            "",
            "",
            "TUE",
            "10:00",
            "11:15",
        ],
    ]


def test_rows_unknown_day_falls_back_to_number():
    """Test that an unknown day number is displayed as its number."""
    schedules = [
        [
            {
                "course": "C",
                "faculty": "F",
                "times": [
                    {
                        "day": 6,
                        "start": 0,
                        "duration": 30,
                    }
                ],
            }
        ]
    ]

    assert mod._rows(schedules)[0][5] == "6"


def test_rows_empty():
    """Test that empty schedules produce no rows."""
    assert mod._rows([]) == []
    assert mod._rows([[]]) == []


def test_rows_missing_required_key_raises():
    """Test that a missing required course key raises KeyError."""
    schedules = [
        [
            {
                "faculty": "F",
                "times": [
                    {
                        "day": 1,
                        "start": 480,
                        "duration": 50,
                    }
                ],
            }
        ]
    ]

    with pytest.raises(KeyError):
        mod._rows(schedules)


# ----------------------------------------------------------------------
# _read_csv tests
# ----------------------------------------------------------------------


def test_read_csv_parses_times_and_strips_caret(tmp_path):
    """Test CSV parsing and removal of the trailing caret."""
    path = tmp_path / "s.csv"

    path.write_text(
        'CS101,Smith,R1,L1,'
        '"MON 08:00-08:50, WED 08:00-08:50^"\n'
    )

    assert mod._read_csv(path) == [
        [
            "1",
            "CS101",
            "Smith",
            "R1",
            "L1",
            "MON",
            "08:00",
            "08:50",
        ],
        [
            "1",
            "CS101",
            "Smith",
            "R1",
            "L1",
            "WED",
            "08:00",
            "08:50",
        ],
    ]


def test_read_csv_blank_lines_separate_schedules(tmp_path):
    """Test that blank lines separate different schedules."""
    path = tmp_path / "s.csv"

    path.write_text(
        "\n"
        "A,F1,R,L,MON 08:00-09:00\n"
        "B,F2,R,L,TUE 09:00-10:00\n"
        "\n"
        ",,,,\n"
        "C,F3,R,L,FRI 10:00-11:00\n"
    )

    numbers = [
        row[0]
        for row in mod._read_csv(path)
    ]

    assert numbers == ["1", "1", "2"]


def test_read_csv_skips_short_lines_and_empty_times(tmp_path):
    """Test that invalid short rows and empty times are ignored."""
    path = tmp_path / "s.csv"

    path.write_text(
        'too,short\n'
        'A,F,R,L,"MON 08:00-09:00,,"\n'
    )

    rows = mod._read_csv(path)

    assert len(rows) == 1
    assert rows[0][1] == "A"


def test_read_csv_malformed_time_raises(tmp_path):
    """Test that malformed time data raises ValueError."""
    path = tmp_path / "s.csv"

    path.write_text(
        "A,F,R,L,MON0800\n"
    )

    with pytest.raises(ValueError):
        mod._read_csv(path)


# ----------------------------------------------------------------------
# display_schedules tests
# ----------------------------------------------------------------------


def test_no_files(workdir):
    """Test the message shown when no schedule files exist."""
    console = FakeConsole()

    run_display(console)

    assert console.lines == [
        "No CSV or JSON schedule files found."
    ]

    assert console.prompts == []


def test_lists_files_sorted_with_letters(workdir):
    """Test that CSV and JSON files are listed alphabetically."""
    (workdir / "b.json").write_text("[]")
    (workdir / "a.csv").write_text("")
    (workdir / "notes.txt").write_text("ignored")

    console = FakeConsole(answers=["a"])

    run_display(console)

    assert "A. a.csv" in console.lines
    assert "B. b.json" in console.lines
    assert "notes.txt" not in console.output


def test_invalid_choices_reprompt(workdir):
    """Test that invalid choices cause the program to ask again."""
    (workdir / "a.json").write_text("[]")

    console = FakeConsole(
        answers=["", "zz", "B", "1", " a "]
    )

    run_display(console)

    assert len(console.prompts) == 5

    assert (
        console.lines.count(
            "Please choose one of the listed options."
        )
        == 4
    )

    assert console.lines[-1] == "No schedules to display."


def test_display_csv(workdir):
    """Test displaying schedules from a CSV file."""
    (workdir / "sched.csv").write_text(
        "CS101,Smith,R1,L1,MON 08:00-08:50\n"
        "\n"
        "CS202,Jones,R2,L2,TUE 10:00-11:15\n"
    )

    console = FakeConsole(answers=["A"])

    run_display(console)

    out = console.output

    assert "Displaying sched.csv" in out
    assert "Schedule 1" in out
    assert "Schedule 2" in out
    assert "CS101" in out
    assert "CS202" in out
    assert "10:00" in out
    assert "11:15" in out


def test_display_json(workdir):
    """Test displaying schedules from a JSON file."""
    data = [
        [
            {
                "course": "CS101",
                "faculty": "Smith",
                "room": "R1",
                "times": [
                    {
                        "day": 4,
                        "start": 780,
                        "duration": 50,
                    }
                ],
            }
        ]
    ]

    (workdir / "sched.json").write_text(
        json.dumps(data)
    )

    console = FakeConsole(answers=["A"])

    run_display(console)

    out = console.output

    assert "Displaying sched.json" in out
    assert "Schedule 1" in out
    assert "THU" in out
    assert "13:00" in out
    assert "13:50" in out


def test_empty_csv_says_nothing_to_display(workdir):
    """Test that an empty CSV produces the correct message."""
    (workdir / "empty.csv").write_text("\n\n")

    console = FakeConsole(answers=["A"])

    run_display(console)

    assert console.lines[-1] == "No schedules to display."


def test_empty_json_says_nothing_to_display(workdir):
    """Test that an empty JSON file produces the correct message."""
    (workdir / "empty.json").write_text("[]")

    console = FakeConsole(answers=["A"])

    run_display(console)

    assert console.lines[-1] == "No schedules to display."


def test_invalid_json_message(workdir):
    """Test the error message for invalid JSON."""
    (workdir / "bad.json").write_text("{not json")

    console = FakeConsole(answers=["A"])

    run_display(console)

    assert (
        console.lines[-1]
        == "Could not read bad.json: the file is not valid JSON."
    )


def test_malformed_csv_message(workdir):
    """Test the error message for malformed CSV."""
    (workdir / "bad.csv").write_text(
        "A,F,R,L,MON0800\n"
    )

    console = FakeConsole(answers=["A"])

    run_display(console)

    assert (
        console.lines[-1]
        == "Could not read bad.csv: "
        "the schedule format is invalid."
    )


def test_file_deleted_after_listing(workdir, monkeypatch):
    """Test the error message when a selected file disappears."""
    path = workdir / "gone.json"
    path.write_text("[]")

    console = FakeConsole(answers=["A"])

    original_ask = console.ask

    def ask_then_delete(prompt):
        """Delete the file before returning the user's answer."""
        path.unlink()
        return original_ask(prompt)

    monkeypatch.setattr(
        console,
        "ask",
        ask_then_delete,
    )

    run_display(console)

    assert (
        console.lines[-1]
        == "No schedule file found at gone.json."
    )


def test_spec_registered():
    """Test that the display command is registered."""
    assert any(
        spec.handler is mod.display_schedules
        for spec in mod.SPECS
    )