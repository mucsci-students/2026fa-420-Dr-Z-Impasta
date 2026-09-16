"""The interactive export step shared by the run and results commands."""

from zimpasta.console import Console
from zimpasta.export import ExportFormat, ExportResult, export_schedules
from zimpasta.generate import Schedule
from zimpasta.prompts import (
    UNWRITABLE_FILENAME,
    VALID_FILENAME_PROMPT,
    OutputTarget,
    ask_output_path,
    ask_yes_no,
    overwrite_prompt,
)


def export_with_prompts(
    console: Console,
    schedules: list[Schedule],
    fmt: ExportFormat,
    target: OutputTarget,
) -> ExportResult:
    """Export ``schedules`` to ``target``, re-prompting on overwrite refusals and write errors.

    A file that appeared since the name was chosen triggers the overwrite confirmation; a
    ``no`` there, or any write failure, returns to the file-name prompt. Every path ends
    with a successful export and a line reporting the location.
    """
    while True:
        try:
            result = export_schedules(schedules, target.path, fmt, overwrite=target.overwrite)
        except FileExistsError:
            if ask_yes_no(console, overwrite_prompt(target.path)):
                target = OutputTarget(target.path, overwrite=True)
            else:
                target = ask_output_path(console, fmt)
            continue
        except OSError:
            console.say(UNWRITABLE_FILENAME)
            target = ask_output_path(console, fmt, first_prompt=f"{VALID_FILENAME_PROMPT} ")
            continue
        console.say(f"Wrote {result.schedule_count} schedule(s) to {result.path}")
        return result
