"""Display schedules from CSV or JSON files."""

import csv
import io
import json
from pathlib import Path

from rich.console import Console as RichConsole
from rich.table import Table

from zimpasta.command import CommandSpec, Invocation
from zimpasta.console import Console
from zimpasta.session import Session

DAYS = {1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI"}

HEADER = ["Schedule", "Course", "Faculty", "Room", "Lab", "Day", "Start", "End"]


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _rows(schedules: list) -> list[list[str]]:
    rows = []

    for index, schedule in enumerate(schedules, start=1):
        for assignment in schedule:
            for meeting in assignment["times"]:
                start = meeting["start"]

                rows.append(
                    [
                        str(index),
                        assignment["course"],
                        assignment["faculty"],
                        assignment.get("room", ""),
                        assignment.get("lab", ""),
                        DAYS.get(meeting["day"], str(meeting["day"])),
                        _clock(start),
                        _clock(start + meeting["duration"]),
                    ]
                )

    return rows


def _read_csv(path: Path) -> list[list[str]]:
    rows = []
    schedule_number = 1
    has_schedule = False

    with open(path, newline="") as handle:
        reader = csv.reader(handle)

        for line in reader:
            # Blank lines separate schedules.
            if not line or not any(cell.strip() for cell in line):
                if has_schedule:
                    schedule_number += 1
                    has_schedule = False
                continue

            if len(line) < 5:
                continue

            course = line[0]
            faculty = line[1]
            room = line[2]
            lab = line[3]
            times = line[4]

            # Remove the ^ at the end of the time information.
            times = times.rstrip("^")

            for time in times.split(","):
                time = time.strip()

                if not time:
                    continue

                day, clock = time.split(" ", 1)
                start, end = clock.split("-", 1)

                rows.append(
                    [
                        str(schedule_number),
                        course,
                        faculty,
                        room,
                        lab,
                        day,
                        start,
                        end.rstrip("^"),
                    ]
                )

            has_schedule = True

    return rows

def _print_table(console: Console, path: Path, rows: list[list[str]]) -> None:
    buffer = io.StringIO()

    rich_console = RichConsole(
        file=buffer,
        force_terminal=False,
        color_system=None,
    )

    rich_console.print(f"Displaying {path.name}")

    schedules = {}

    for row in rows:
        schedule_number = row[0]
        schedules.setdefault(schedule_number, []).append(row[1:])

    for schedule_number, schedule_rows in schedules.items():
        table = Table(title=f"Schedule {schedule_number}")

        for heading in HEADER[1:]:
            table.add_column(heading)

        for row in schedule_rows:
            table.add_row(*row)

        rich_console.print(table)
        rich_console.print()

    for line in buffer.getvalue().splitlines():
        console.say(line)

def _display_csv(console: Console, path: Path) -> None:
    rows = _read_csv(path)

    if not rows:
        console.say("No schedules to display.")
        return

    _print_table(console, path, rows)


def _display_json(console: Console, path: Path) -> None:
    with open(path) as handle:
        schedules = json.load(handle)

    rows = _rows(schedules)

    if not rows:
        console.say("No schedules to display.")
        return

    _print_table(console, path, rows)


def display_schedules(
    console: Console,
    session: Session,
    invocation: Invocation,
) -> None:
    files = sorted(
        list(Path(".").glob("*.json"))
        + list(Path(".").glob("*.csv"))
    )

    if not files:
        console.say("No CSV or JSON schedule files found.")
        return

    console.say("")
    console.say("Available schedule files:")

    for index, file in enumerate(files):
        letter = chr(ord("A") + index)
        console.say(f"{letter}. {file.name}")

    console.say("")

    while True:
        choice = console.ask("Choose a file: ").strip().upper()

        if len(choice) == 1 and "A" <= choice <= "Z":
            index = ord(choice) - ord("A")

            if index < len(files):
                path = files[index]
                break

        console.say("Please choose one of the listed options.")

    try:
        if path.suffix.lower() == ".csv":
            _display_csv(console, path)
        else:
            _display_json(console, path)

    except FileNotFoundError:
        console.say(f"No schedule file found at {path}.")
    except json.JSONDecodeError:
        console.say(f"Could not read {path}: the file is not valid JSON.")
    except (ValueError, IndexError):
        console.say(f"Could not read {path}: the schedule format is invalid.")


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "display",
        description="Display schedules",
        handler=display_schedules,
    ),
)

