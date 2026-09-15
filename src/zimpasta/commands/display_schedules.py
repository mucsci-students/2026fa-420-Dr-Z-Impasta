"""Display schedules from CSV or JSON files."""

import csv
import io
import json
from pathlib import Path

from zimpasta.command import CommandSpec, Invocation
from zimpasta.console import Console
from zimpasta.session import Session

DAYS = {1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI"}

HEADER = ["schedule", "course", "faculty", "room", "lab", "day", "start", "end"]


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

    with open(path, newline="") as handle:
        reader = csv.reader(handle)

        for line in reader:
            if not line:
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

                day, clock = time.split(" ", 1)
                start, end = clock.split("-")

                rows.append(
                    [
                        course,
                        faculty,
                        room,
                        lab,
                        day,
                        start,
                        end,
                    ]
                )

    return rows


def _display_csv(console: Console, path: Path) -> None:
    rows = _read_csv(path)

    if not rows:
        console.say("No schedules to display.")
        return

    console.say("")
    console.say(f"Displaying {path.name}:")
    console.say("")

    console.say("course,faculty,room,lab,day,start,end")

    for row in rows:
        console.say(",".join(row))


def _display_json(console: Console, path: Path) -> None:
    with open(path) as handle:
        schedules = json.load(handle)

    rows = _rows(schedules)

    if not rows:
        console.say("No schedules to display.")
        return

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(HEADER)
    writer.writerows(rows)

    console.say("")
    console.say(f"Displaying {path.name}:")
    console.say("")

    for line in buffer.getvalue().splitlines():
        console.say(line)


def display_schedules(
    console: Console,
    session: Session,
    invocation: Invocation,
) -> None:

    files = sorted(list(Path(".").glob("*.json")) + list(Path(".").glob("*.csv")))

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


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "display",
        description="Display schedules",
        handler=display_schedules,
    ),
)
