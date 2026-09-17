"""Display schedules from CSV or JSON files.

This module provides the ``display`` command for loading schedule files
from the current directory and displaying their contents in formatted
tables.

Both CSV and JSON schedule files are supported. Users are shown a list
of available files and can select a file by using the letter assigned to
that file.

CSV files use blank lines to separate different schedules. JSON files
contain schedules as nested lists of assignments.
"""

import csv
import io
import json
from pathlib import Path

from rich.console import Console as RichConsole
from rich.table import Table

from zimpasta.command import CommandSpec, Invocation
from zimpasta.console import Console
from zimpasta.session import Session


# Mapping of numeric day values used by JSON schedules to their
# three-letter day abbreviations.
DAYS = {
    1: "MON",
    2: "TUE",
    3: "WED",
    4: "THU",
    5: "FRI",
}


# Column headings used when displaying schedule information.
HEADER = [
    "Schedule",
    "Course",
    "Faculty",
    "Room",
    "Lab",
    "Day",
    "Start",
    "End",
]


def _clock(minutes: int) -> str:
    """Convert a number of minutes after midnight to a clock time.

    Args:
        minutes: The number of minutes after midnight.

    Returns:
        A time string in ``HH:MM`` format.

    Example:
        ``480`` is converted to ``"08:00"``.
    """
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _rows(schedules: list) -> list[list[str]]:
    """Convert JSON schedule data into table rows.

    Each meeting in each assignment becomes one row. The schedule
    number is added to each row so that meetings can later be grouped
    into their corresponding schedules.

    Args:
        schedules: A list of schedules. Each schedule contains
            assignments, and each assignment contains one or more
            meetings in its ``times`` field.

    Returns:
        A list of rows containing schedule, course, faculty, room,
        laboratory, day, start time, and end time information.

    Raises:
        KeyError: If a required assignment or meeting field is missing.
    """
    rows = []

    # Enumerate schedules starting at 1 so that users see schedule
    # numbers beginning with Schedule 1.
    for index, schedule in enumerate(schedules, start=1):

        # Each schedule may contain multiple course assignments.
        for assignment in schedule:

            # Each course assignment may have multiple meeting times.
            for meeting in assignment["times"]:
                start = meeting["start"]

                rows.append(
                    [
                        str(index),
                        assignment["course"],
                        assignment["faculty"],
                        assignment.get("room", ""),
                        assignment.get("lab", ""),
                        DAYS.get(
                            meeting["day"],
                            str(meeting["day"]),
                        ),
                        _clock(start),
                        _clock(start + meeting["duration"]),
                    ]
                )

    return rows


def _read_csv(path: Path) -> list[list[str]]:
    """Read a CSV schedule file and convert it into table rows.

    Blank lines are used to separate different schedules. Each
    non-empty CSV row represents a course assignment. If a row contains
    multiple meeting times, a separate table row is created for each
    meeting.

    Args:
        path: The path to the CSV schedule file.

    Returns:
        A list of rows containing schedule, course, faculty, room,
        laboratory, day, start time, and end time information.

    Raises:
        ValueError: If a meeting time does not have the expected format.
        OSError: If the file cannot be opened or read.
    """
    rows = []
    schedule_number = 1
    has_schedule = False

    # Open the CSV file with newline handling appropriate for csv.reader.
    with open(path, newline="") as handle:
        reader = csv.reader(handle)

        for line in reader:

            # Blank lines separate schedules. Multiple consecutive blank
            # lines do not create additional empty schedules.
            if not line or not any(cell.strip() for cell in line):
                if has_schedule:
                    schedule_number += 1
                    has_schedule = False
                continue

            # Ignore malformed rows that do not contain all five
            # expected CSV fields.
            if len(line) < 5:
                continue

            course = line[0]
            faculty = line[1]
            room = line[2]
            lab = line[3]
            times = line[4]

            # Remove the caret that may appear at the end of the
            # time information.
            times = times.rstrip("^")

            # A course may have multiple meeting times separated by
            # commas.
            for time in times.split(","):
                time = time.strip()

                # Ignore empty time entries.
                if not time:
                    continue

                # Separate the day from the clock range.
                day, clock = time.split(" ", 1)

                # Separate the start and end times.
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

            # Mark that the current schedule contains data.
            has_schedule = True

    return rows


def _print_table(
    console: Console,
    path: Path,
    rows: list[list[str]],
) -> None:
    """Format schedule rows as Rich tables and send them to the console.

    Rich normally writes formatted output directly to the terminal.
    This function first writes the table output to an in-memory buffer.
    The resulting lines are then sent through the project's ``Console``
    object using ``console.say()``.

    Args:
        console: The project's console used to display output.
        path: The path of the schedule file being displayed.
        rows: The schedule rows to display.

    Returns:
        None.
    """
    buffer = io.StringIO()

    # Create a Rich console that writes to the in-memory buffer.
    # Terminal colors are disabled so the output can be passed through
    # the project's console without terminal-specific formatting.
    rich_console = RichConsole(
        file=buffer,
        force_terminal=False,
        color_system=None,
    )

    # Display the name of the schedule file.
    rich_console.print(f"Displaying {path.name}")

    # Group rows by schedule number.
    schedules = {}

    for row in rows:
        schedule_number = row[0]
        schedules.setdefault(schedule_number, []).append(row[1:])

    # Create one table for each schedule.
    for schedule_number, schedule_rows in schedules.items():
        table = Table(title=f"Schedule {schedule_number}")

        # Add the table columns. The Schedule column is excluded because
        # the schedule number is already included in the table title.
        for heading in HEADER[1:]:
            table.add_column(heading)

        # Add each course meeting to the table.
        for row in schedule_rows:
            table.add_row(*row)

        rich_console.print(table)
        rich_console.print()

    # Send each line of the formatted Rich output through the project's
    # console implementation.
    for line in buffer.getvalue().splitlines():
        console.say(line)


def _display_csv(console: Console, path: Path) -> None:
    """Read and display a CSV schedule file.

    Args:
        console: The project's console used to display output.
        path: The path to the CSV schedule file.

    Returns:
        None.

    If the CSV file does not contain any schedule rows, a message is
    displayed instead of an empty table.
    """
    rows = _read_csv(path)

    if not rows:
        console.say("No schedules to display.")
        return

    _print_table(console, path, rows)


def _display_json(console: Console, path: Path) -> None:
    """Read and display a JSON schedule file.

    Args:
        console: The project's console used to display output.
        path: The path to the JSON schedule file.

    Returns:
        None.

    Raises:
        json.JSONDecodeError: If the file does not contain valid JSON.
    """
    # Load the JSON schedule data from the file.
    with open(path) as handle:
        schedules = json.load(handle)

    # Convert the JSON data into rows that can be displayed in tables.
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
    """Display a schedule selected from an available CSV or JSON file.

    The command searches the current directory for CSV and JSON files,
    displays them as a lettered list, and asks the user to select one.
    The selected file is then read and displayed as one or more tables.

    Args:
        console: The project's console used for displaying messages and
            receiving user input.
        session: The current application session. This parameter is
            required by the command interface but is not used directly
            by this command.
        invocation: Information about the command invocation. This
            parameter is required by the command interface but is not
            used directly by this command.

    Returns:
        None.

    The command displays an error message if:
        - No CSV or JSON files are found.
        - The user enters an invalid file selection.
        - The selected file no longer exists.
        - A JSON file contains invalid JSON.
        - A schedule file contains an invalid format.
    """

    # Find all JSON and CSV files in the current directory and sort
    # them alphabetically by filename.
    files = sorted(
        list(Path(".").glob("*.json"))
        + list(Path(".").glob("*.csv"))
    )

    # If no schedule files are available, there is nothing to display.
    if not files:
        console.say("No CSV or JSON schedule files found.")
        return

    console.say("")
    console.say("Available schedule files:")

    # Assign a letter to each file so the user can select it easily.
    for index, file in enumerate(files):
        letter = chr(ord("A") + index)
        console.say(f"{letter}. {file.name}")

    console.say("")

    # Continue asking until the user selects a valid file.
    while True:
        choice = console.ask("Choose a file: ").strip().upper()

        # Convert the letter selection into a list index.
        if len(choice) == 1 and "A" <= choice <= "Z":
            index = ord(choice) - ord("A")

            # Make sure the selected letter corresponds to an existing
            # file.
            if index < len(files):
                path = files[index]
                break

        # The user entered an invalid selection.
        console.say("Please choose one of the listed options.")

    try:
        # Use the appropriate reader based on the file extension.
        if path.suffix.lower() == ".csv":
            _display_csv(console, path)
        else:
            _display_json(console, path)

    # Handle the case where the file disappears after the file list
    # was displayed.
    except FileNotFoundError:
        console.say(f"No schedule file found at {path}.")

    # Handle invalid JSON syntax.
    except json.JSONDecodeError:
        console.say(
            f"Could not read {path}: the file is not valid JSON."
        )

    # Handle invalid schedule formatting, including malformed CSV
    # meeting times or invalid list indexes.
    except (ValueError, IndexError):
        console.say(
            f"Could not read {path}: the schedule format is invalid."
        )


# Register the display command with the application.
#
# The command name is "display", and its handler is the
# display_schedules() function.
SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "display",
        description="Display schedules",
        handler=display_schedules,
    ),
)