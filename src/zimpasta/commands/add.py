"""The ``add`` command: register a new course, room, lab, or faculty member.

Field names below match sample_config.json's schema:
  room/lab : name, capacity
  course   : course_id, credits, capacity  (+ room/lab/conflicts/faculty lists)
  faculty  : name, maximum_credits, minimum_credits, unique_course_limit
             (+ maximum_days, mandatory_days, times, *_preferences)

The parenthesized fields are lists or nested mappings. zimpasta.command's grammar
(Positional/Option) only carries scalar strings, so there's no clean one-line way to
set them here. This module deliberately only collects the scalar fields on add;
the list/dict fields default empty and are meant to be filled in afterward, one at a
time, with 'modify' (whose value positional is already optional -- built for exactly
this kind of multi-step edit). Confirm this split is actually what's wanted.
"""

from zimpasta.command import CommandError, CommandSpec, Invocation, Option, Positional
from zimpasta.console import Console
from zimpasta.prompts import ask_choice, ask_int
from zimpasta.session import Session

KINDS = ("course", "room", "lab", "faculty")


NO_CONFIG = "No configuration loaded. Run 'load <path>' first."

# The scalar fields each kind needs beyond its id, matching sample_config.json.
# Keyed by the exact --option name used on the command line.
REQUIRED_INT_FIELDS: dict[str, tuple[str, ...]] = {
    "room": ("capacity",),
    "lab": ("capacity",),
    "course": ("credits", "capacity"),
    "faculty": ("maximum-credits", "minimum-credits", "unique-course-limit"),
}


def _label(kind: str, field: str) -> str:
    """'faculty', 'maximum-credits' -> 'Faculty maximum credits'."""
    return f"{kind.capitalize()} {field.replace('-', ' ')}"


def _build(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    """Fill in kind, id, and then whichever kind-specific numbers are still missing.

    evaluate() calls a builder only when kind or id (the spec's required Positionals)
    are missing -- Option.required can't vary by kind, so a one-liner like
    'add room R1' looks "complete" to the framework even without --capacity. That
    case is caught in _add() instead, on every path, not just this one.
    """
    positionals = dict(invocation.positionals)
    options = dict(invocation.options)

    if "kind" not in positionals:
        positionals["kind"] = ask_choice(console, "Add what? ", KINDS)
    kind = positionals["kind"]

    if "id" not in positionals:
        item_id = console.ask(f"{kind.capitalize()} id: ").strip()
        if not item_id:
            console.say("An id is required.")
            return None
        positionals["id"] = item_id

    for field in REQUIRED_INT_FIELDS.get(kind, ()):
        if field not in options:
            # ask_int already loops until it gets a valid non-negative whole number.
            options[field] = str(ask_int(console, f"{_label(kind, field)}: ", minimum=0))

    return invocation.with_values(positionals=positionals, options=options)


def _required_int(invocation: Invocation, kind: str, field: str) -> int:
    """Read and validate one --field for the given kind, on any code path (typed or built)."""
    raw = invocation.get(field)
    if raw is None:
        raise CommandError(f"--{field} is required for {kind}.")
    try:
        return int(str(raw))
    except ValueError:
        raise CommandError(f"--{field} must be a whole number.") from None


def _add(console: Console, session: Session, invocation: Invocation) -> None:
    """Create the item inside session.config, through its edit_mode()."""
    if not session.has_config:
        raise CommandError(NO_CONFIG)

    kind = str(invocation.get("kind"))
    item_id = str(invocation.get("id"))
    fields = {
        field: _required_int(invocation, kind, field) for field in REQUIRED_INT_FIELDS.get(kind, ())
    }

    # TODO: unverified against the real scheduler.CombinedConfig -- confirm method
    # names/signatures once available. Guessed straight from sample_config.json's
    # field names: room/lab/conflicts/faculty on a course, and maximum_days/
    # mandatory_days/times/*_preferences on faculty, are left at their defaults
    # (empty/None) here and are expected to be set later via 'modify'.
    try:
        with session.config.edit_mode() as edit:
            if kind == "room":
                edit.add_room(item_id, fields["capacity"])
            elif kind == "lab":
                edit.add_lab(item_id, fields["capacity"])
            elif kind == "course":
                edit.add_course(item_id, fields["credits"], fields["capacity"])
            elif kind == "faculty":
                edit.add_faculty(
                    item_id,
                    fields["maximum-credits"],
                    fields["minimum-credits"],
                    fields["unique-course-limit"],
                )
    except ValueError as exc:
        raise CommandError(str(exc)) from exc

    console.say(f"Added {kind} '{item_id}'.")


add_spec = CommandSpec(
    "add",
    positionals=(Positional("kind", choices=KINDS), Positional("id")),
    options=(
        Option("capacity", help="seating/room capacity (room, lab, course)"),
        Option("credits", help="credit hours (course)"),
        Option("maximum-credits", help="maximum credits assignable (faculty)"),
        Option("minimum-credits", help="minimum credits assignable (faculty)"),
        Option("unique-course-limit", help="distinct courses this faculty may teach"),
    ),
    description="Add a course, room, lab, or faculty member",
    handler=_add,
    builder=_build,
)

SPECS: tuple[CommandSpec, ...] = (add_spec,)
