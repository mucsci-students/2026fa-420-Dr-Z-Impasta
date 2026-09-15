"""Display a schedule from a JSON file."""

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

                rows.append([
                    str(index),
                    assignment["course"],
                    assignment["faculty"],
                    assignment.get("room", ""),
                    assignment.get("lab", ""),
                    DAYS.get(meeting["day"], str(meeting["day"])),
                    _clock(start),
                    _clock(start + meeting["duration"]),
                ])

    return rows


def display_schedules(
    console: Console,
    session: Session,
    invocation: Invocation,
) -> None:

    files = sorted(Path(".").glob("*.json"))

    if not files:
        console.say("No JSON schedule files found.")
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
        with open(path) as handle:
            schedules = json.load(handle)

    except FileNotFoundError:
        console.say(f"No schedule file found at {path}.")
        return

    except json.JSONDecodeError:
        console.say(f"Could not read {path}: the file is not valid JSON.")
        return

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
    
    for line in buffer.getvalue().splitlines():
        console.say(line)


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "display",
        description="Display schedules",
        handler=display_schedules,
    ),
)