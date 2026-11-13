"""Delete a room, lab, course, or faculty member from the loaded configuration.

``delete course "CS 101"`` runs straight away; a bare ``delete``, or one missing the
item, asks which category and which item through numbered menus. Either way the handler
confirms before touching the configuration.

A course id is not unique: a configuration may offer the same course several times, once
per section, and those entries differ in their rooms, conflicts, and faculty. Items are
therefore identified by position, and ``--section`` picks between entries that share a
name. A name that matches one entry needs no ``--section``; a name that matches several
is refused rather than guessed at, because deleting the wrong section is silent.

Deleting an item also strips every reference to it, because the library rejects a
configuration whose courses or faculty point at a name that no longer exists. References
name a course, not a section, so they are stripped only when the last entry of that name
goes. The references are cleared before the entry itself is removed: ``validate_assignment``
re-runs cross-reference validation on every assignment, so removing the entry first
would fail against references that are about to be cleaned up anyway.
"""

from dataclasses import dataclass

from pydantic import ValidationError

from zimpasta.command import CommandSpec, Invocation, Option, Positional
from zimpasta.commands.common import KINDS
from zimpasta.commands.common import NO_CONFIG_TO_EDIT as NO_CONFIG
from zimpasta.console import Console
from zimpasta.prompts import ask_menu, ask_yes_no
from zimpasta.session import Session

NOTHING_TO_DELETE = "There is nothing of that type to delete."
NOT_FOUND = "There is no {kind} named {name}."
CANCELLED = "Cancelled. Nothing was deleted."
DELETED = "Deleted {name}."
WOULD_LEAVE_INVALID = "Can't delete {name}: {error}"
AMBIGUOUS = "There are {count} entries named {name}. Add --section 1-{count} to choose one."
BAD_SECTION = "--section must be a number between 1 and {count}."

SECTION_LABEL = "{name} (section {number} of {count})"
"""How an entry is shown when it shares its name with another."""

CANCEL = "Cancel"


@dataclass(frozen=True)
class _Reference:
    """A field of every entry in ``where`` that may name an entry being deleted."""

    where: str
    field: str
    empty_means_none: bool = False
    """An empty list is rejected here, and ``None`` means "derive from preferences"."""


@dataclass(frozen=True)
class _Kind:
    """Where one kind of entry lives, what names it, and what refers to it."""

    items: str
    name: str
    references: tuple[_Reference, ...]
    """Stripped in this order, only when the last entry of that name goes."""


_KINDS = {
    "room": _Kind(
        "rooms", "name", (_Reference("courses", "room"), _Reference("faculty", "room_preferences"))
    ),
    "lab": _Kind(
        "labs", "name", (_Reference("courses", "lab"), _Reference("faculty", "lab_preferences"))
    ),
    # Conflicts and preferences name a course, so they outlive its other sections.
    "course": _Kind(
        "courses",
        "course_id",
        (_Reference("courses", "conflicts"), _Reference("faculty", "course_preferences")),
    ),
    "faculty": _Kind("faculty", "name", (_Reference("courses", "faculty", empty_means_none=True),)),
}


def _names(scheduler, kind: str) -> list[str]:
    """Names of every entry of ``kind``, in display order. Course ids may repeat."""
    spec = _KINDS[kind]
    return [getattr(entry, spec.name) for entry in getattr(scheduler, spec.items)]


def _label(names: list[str], index: int) -> str:
    """How entry ``index`` is named to the user: bare, or numbered when the name repeats."""
    name = names[index]
    matches = [position for position, other in enumerate(names) if other == name]
    if len(matches) == 1:
        return name
    return SECTION_LABEL.format(name=name, number=matches.index(index) + 1, count=len(matches))


def _resolve(names: list[str], kind: str, name: str, section: str | None) -> int | str:
    """The index ``name`` (and ``section``) refers to, or a message saying why it does not."""
    matches = [position for position, other in enumerate(names) if other == name]
    if not matches:
        return NOT_FOUND.format(kind=kind, name=name)
    if section is None:
        if len(matches) > 1:
            return AMBIGUOUS.format(count=len(matches), name=name)
        return matches[0]
    if not section.isdecimal() or not 1 <= int(section) <= len(matches):
        return BAD_SECTION.format(count=len(matches))
    return matches[int(section) - 1]


def _last_of_its_name(names: list[str], index: int) -> bool:
    """Whether removing ``index`` leaves no other entry of the same name behind."""
    return not any(
        other == names[index] for position, other in enumerate(names) if position != index
    )


def _without(value, name: str, reference: _Reference):
    """``value`` (a list of names, or a dict keyed by name) with ``name`` taken out."""
    if isinstance(value, dict):
        return {key: rank for key, rank in value.items() if key != name}
    kept = [other for other in value if other != name]
    return (kept or None) if reference.empty_means_none else kept


def _remove(scheduler, kind: str, index: int) -> None:
    """Remove entry ``index`` of ``kind``, first stripping every reference to its name."""
    spec = _KINDS[kind]
    name = getattr(getattr(scheduler, spec.items)[index], spec.name)
    if _last_of_its_name(_names(scheduler, kind), index):
        for reference in spec.references:
            for holder in getattr(scheduler, reference.where):
                value = getattr(holder, reference.field)
                if value is not None:  # None (derive from preferences) names no one
                    setattr(holder, reference.field, _without(value, name, reference))
    entries = getattr(scheduler, spec.items)
    setattr(
        scheduler,
        spec.items,
        [entry for position, entry in enumerate(entries) if position != index],
    )


def build(console: Console, session: Session, invocation: Invocation) -> Invocation | None:
    """Ask which category and which entry, listing only what the configuration holds."""
    if session.config is None:
        console.say(NO_CONFIG)
        return None

    kind = invocation.get("kind")
    if kind is None:
        choice = ask_menu(console, "Delete what?", [*KINDS, CANCEL])
        if choice == len(KINDS) + 1:
            console.say(CANCELLED)
            return None
        kind = KINDS[choice - 1]

    if invocation.get("id") is not None:
        return invocation.with_values({"kind": str(kind)})

    names = _names(session.config.config, str(kind))
    if not names:
        console.say(NOTHING_TO_DELETE)
        return None
    labels = [_label(names, index) for index in range(len(names))]
    choice = ask_menu(console, f"Delete which {kind}?", [*labels, CANCEL])
    if choice == len(names) + 1:
        console.say(CANCELLED)
        return None

    index = choice - 1
    chosen = invocation.with_values({"kind": str(kind), "id": names[index]})
    # Name the section only when the name alone would not pick this entry back out.
    matches = [position for position, other in enumerate(names) if other == names[index]]
    if len(matches) > 1:
        chosen = chosen.with_values(options={"section": str(matches.index(index) + 1)})
    return chosen


def delete(console: Console, session: Session, invocation: Invocation) -> None:
    """Confirm, then remove the entry and every reference left dangling by it."""
    if session.config is None:
        console.say(NO_CONFIG)
        return
    config = session.config
    kind = str(invocation.get("kind"))
    name = str(invocation.get("id"))
    section = invocation.get("section")

    names = _names(config.config, kind)
    resolved = _resolve(names, kind, name, None if section is None else str(section))
    if isinstance(resolved, str):
        console.say(resolved)
        return

    label = _label(names, resolved)
    if not ask_yes_no(console, f"Delete {kind} '{label}'? (yes/no): "):
        console.say(CANCELLED)
        return

    try:
        with config.edit_mode() as working:
            _remove(working.config, kind, resolved)
    except ValidationError as error:
        console.say(WOULD_LEAVE_INVALID.format(name=label, error=error))
        return

    console.say(DELETED.format(name=label))


SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "delete",
        positionals=(Positional("kind", choices=KINDS), Positional("id")),
        options=(Option("section", help="which entry, when several share the name"),),
        description="Remove an item",
        handler=delete,
        builder=build,
    ),
)
