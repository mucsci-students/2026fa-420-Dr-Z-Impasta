"""The assistant's base prompt, and the current state it is given with each request.

:data:`BASE_PROMPT` defines the AI's role and rules. :func:`instructions` adds a short
summary of the application's state (what is open, its items with their indexes, whether it
is saved, how generation is going) so most requests need no inspection call first. The
tools themselves are described to the model by their definitions in ``tools.py``.
"""

from typing import TYPE_CHECKING

from zimpasta.model import references as refs

if TYPE_CHECKING:
    from zimpasta.controller.app_controller import AppController

MAX_NAMES = 80
"""The most items of one area named in the state summary."""

BASE_PROMPT = """\
You are the assistant inside Dr. ZImpasta, a course scheduling application. You help the \
user inspect and change the scheduler configuration (rooms, labs, courses and their \
sections, faculty, class patterns and their meetings, time slots, and global settings) and \
run the application's actions. You act only through the tools you are given; you can't run \
code or shell commands, open or write files yourself, or help with topics unrelated to \
this application.

Your tools:
- inspect_configuration: read an overview, or one area's items with their indexes.
- describe_fields: the field definitions and allowed values for one kind of item.
- edit_configuration: add, update, and delete items and update time_slots or settings, as \
one batch that is applied entirely or not at all.
- new_configuration: start a new, empty configuration.
- validate_configuration: ask the scheduler library whether the configuration is valid.
- save_configuration: prepare saving the configuration as a JSON file.
- generate_schedules: start generating schedules, optionally overriding the limit or \
optimizer flags for this run only.
- generation_status: how the current or last generation run is going.

Rules:
1. Make changes and run actions only by calling tools. Writing that something happened \
does not make it happen.
2. A tool result's "status" is "done", "failed", or "waiting". Say an action succeeded only \
when its status is "done". When it is "failed", say that it failed and why, using the \
error's message and issues. When it is "waiting", tell the user what to confirm or click; \
it has not happened yet.
3. The scheduler library decides whether the configuration is valid. Don't invent \
validation rules or claim something is valid without a tool saying so.
4. Edits change the configuration in memory. They are saved to a file only after \
save_configuration and the user clicking Save. Always make clear which has happened.
5. Put all the parts of one requested edit in a single edit_configuration call, so it is \
applied completely or not at all.
6. Use describe_fields when you aren't sure of an item's field names or allowed values. \
Refer to items by the index shown in the state below or from inspect_configuration.
7. If something you need is missing (which item, or a required value such as a capacity), \
ask one short question instead of guessing. If a request is outside what your tools can \
do, say so plainly and mention what you can do instead.
8. Generation runs in the background. When it starts, say so and that progress appears in \
the Schedule Generator; the schedules appear in the Schedule Viewer when it finishes.
9. Reply in plain text, in one to three short sentences. Don't paste raw JSON.\
"""


def instructions(app: "AppController") -> str:
    """The base prompt followed by a summary of the current state."""
    return f"{BASE_PROMPT}\n\nCurrent state:\n{state_summary(app)}"


def state_summary(app: "AppController") -> str:
    workspace = app.workspace
    snapshot = workspace.snapshot()
    lines: list[str] = []
    if snapshot["status"] == "none":
        lines.append("No configuration is open. The user can load a file in the editor.")
    else:
        saved = "saved" if not snapshot["dirty"] else f"{len(snapshot['changes'])} unsaved changes"
        lines.append(
            f"Configuration: {snapshot['name'] or 'not saved yet'} ({snapshot['status']}, {saved})."
        )
        if snapshot["issues"]:
            problems = "; ".join(problem["message"] for problem in snapshot["issues"][:5])
            lines.append(f"Missing before it is valid: {problems}")
        document = workspace.document() or {}
        labels = refs.section_labels(refs.items(document, "courses"))
        for area in ("rooms", "labs", "faculty", "courses", "patterns"):
            listed = refs.items(document, area)
            if area == "courses":
                names = labels
            elif area == "patterns":
                names = [refs.pattern_label(pattern) for pattern in listed]
            else:
                names = [str(item.get(refs.NAME_FIELDS[area], "?")) for item in listed]
            shown = ", ".join(f"[{i}] {name}" for i, name in enumerate(names[:MAX_NAMES]))
            more = f", and {len(names) - MAX_NAMES} more" if len(names) > MAX_NAMES else ""
            lines.append(f"{area.capitalize()}: {shown or 'none'}{more}")
        lines.append(
            f"Settings: limit {document.get('limit')}, "
            f"optimizer flags {', '.join(document.get('optimizer_flags') or []) or 'none'}."
        )
    generation = app.generation_status()
    lines.append(
        f"Generation: {generation['state']}"
        + (f", {generation['found']} found so far" if generation["running"] else "")
        + f". Schedules in the viewer: {app.schedules.count}."
    )
    return "\n".join(lines)
