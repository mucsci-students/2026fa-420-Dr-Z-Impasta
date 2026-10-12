"""Which configuration items refer to which, for safe deletes and renames.

Rooms, labs, faculty members, and courses are referred to by name from other items:

======================  =================================================================
Item                    Referred to by
======================  =================================================================
room                    a course's ``room`` options; a faculty member's ``room_preferences``
lab                     a course's ``lab`` options; a faculty member's ``lab_preferences``
faculty member          a course's ``faculty`` candidates
course (by id)          other courses' ``conflicts``; faculty ``course_preferences``
======================  =================================================================

Deleting follows the policy shown in the Configuration Editor mockup:

* **Blocking.** If the item is the *only* room, lab, or faculty option a course section
  has, deleting it would change what that section is (a lab section without a lab, a
  section nobody can teach), so the delete is refused until the section is edited.
* **Cascading.** Every other reference is optional (one option among several, a
  preference, a conflict) and is removed along with the item. The caller shows these to
  the user before committing.

A course id names every section with that id, so references to a course are only
touched when its last section is deleted or renamed.

These functions work on plain ``CombinedConfig`` JSON documents and never validate;
the workspace runs the library's validation on the result as the final word.
"""

import copy
from dataclasses import dataclass

from zimpasta.model.issues import COLLECTIONS

NAME_FIELDS: dict[str, str] = {
    "rooms": "name",
    "labs": "name",
    "faculty": "name",
    "courses": "course_id",
}
"""The field that other items use to refer to an item, per area. Patterns have none."""

AREA_NOUNS: dict[str, str] = {
    "rooms": "room",
    "labs": "lab",
    "courses": "course section",
    "faculty": "faculty member",
    "patterns": "class pattern",
}


@dataclass(frozen=True)
class Reference:
    """One place that refers to the item being deleted or renamed."""

    area: str
    """``courses`` or ``faculty``."""

    index: int
    label: str
    """How the referring item is shown, for example ``CMSC 161.02`` or ``Hardy``."""

    field: str
    """The field holding the reference, for example ``room`` or ``lab_preferences``."""

    def to_dict(self) -> dict:
        return {"area": self.area, "index": self.index, "label": self.label, "field": self.field}


@dataclass(frozen=True)
class DeleteImpact:
    """What deleting one item would do to the rest of the configuration."""

    area: str
    index: int
    label: str
    blocking: tuple[Reference, ...] = ()
    """References that make the delete impossible until they are edited."""

    cascades: tuple[Reference, ...] = ()
    """Optional references that are removed together with the item."""

    problems: tuple = ()
    """Library ``Issue``s the delete would still cause after cascading (filled by the workspace)."""

    @property
    def can_delete(self) -> bool:
        return not self.blocking and not self.problems

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "index": self.index,
            "label": self.label,
            "can_delete": self.can_delete,
            "blocking": [reference.to_dict() for reference in self.blocking],
            "cascades": [reference.to_dict() for reference in self.cascades],
            "problems": [problem.to_dict() for problem in self.problems],
        }


def items(document: dict, area: str) -> list[dict]:
    """The list of items for ``area`` inside ``document`` (the live list, not a copy)."""
    section, key = COLLECTIONS[area]
    return document[section][key]


def section_labels(courses: list[dict]) -> list[str]:
    """Display ids for course sections: ``CMSC 140.01``, ``CMSC 140.02``, ...

    An explicit ``section_id`` is used as is; otherwise sections are numbered in
    configuration order among entries with the same ``course_id``, as the library does.
    """
    seen: dict[str, int] = {}
    labels = []
    for course in courses:
        course_id = course["course_id"]
        seen[course_id] = seen.get(course_id, 0) + 1
        suffix = course.get("section_id") or f"{seen[course_id]:02d}"
        labels.append(f"{course_id}.{suffix}")
    return labels


def pattern_label(pattern: dict) -> str:
    """For example ``4 credits: MON (lab), WED``."""
    days = ", ".join(
        f"{meeting['day']} (lab)" if meeting.get("lab") else str(meeting["day"])
        for meeting in pattern.get("meetings", [])
    )
    return f"{pattern['credits']} credits: {days}"


def item_label(document: dict, area: str, index: int) -> str:
    """How item ``index`` of ``area`` is shown to the user."""
    listed = items(document, area)
    if area == "courses":
        return section_labels(listed)[index]
    if area == "patterns":
        return pattern_label(listed[index])
    return str(listed[index][NAME_FIELDS[area]])


def delete_impact(document: dict, area: str, index: int) -> DeleteImpact:
    """Which references deleting item ``index`` of ``area`` would block or remove."""
    label = item_label(document, area, index)
    if area == "patterns":
        return DeleteImpact(area, index, label)
    name = items(document, area)[index][NAME_FIELDS[area]]
    if area == "courses" and _shared_course_id(document, index):
        return DeleteImpact(area, index, label)

    blocking: list[Reference] = []
    cascades: list[Reference] = []
    for owner_area, owner_index, owner_field, values in _references_to(document, area, name):
        reference = Reference(
            owner_area, owner_index, item_label(document, owner_area, owner_index), owner_field
        )
        only_option = owner_field in ("room", "lab", "faculty") and len(values) == 1
        (blocking if only_option else cascades).append(reference)
    return DeleteImpact(area, index, label, tuple(blocking), tuple(cascades))


def apply_delete(document: dict, area: str, index: int) -> dict:
    """A copy of ``document`` without item ``index`` and without its optional references.

    Call :func:`delete_impact` first; blocking references are removed here too, which
    leaves a document the library will reject.
    """
    result = copy.deepcopy(document)
    if area != "patterns" and not (area == "courses" and _shared_course_id(result, index)):
        name = items(result, area)[index][NAME_FIELDS[area]]
        for owner_area, owner_index, owner_field, _ in _references_to(result, area, name):
            owner = items(result, owner_area)[owner_index]
            owner[owner_field] = _without(owner[owner_field], name)
            if owner_field == "faculty" and owner[owner_field] == []:
                owner[owner_field] = None
    del items(result, area)[index]
    return result


def apply_rename(document: dict, area: str, old: str, new: str) -> tuple[dict, int]:
    """A copy of ``document`` with every reference to ``old`` renamed to ``new``.

    Returns the new document and how many references changed. For courses the caller must
    only rename when no other section keeps the old id.
    """
    result = copy.deepcopy(document)
    count = 0
    for owner_area, owner_index, owner_field, _ in _references_to(result, area, old):
        owner = items(result, owner_area)[owner_index]
        owner[owner_field] = _renamed(owner[owner_field], old, new)
        count += 1
    return result, count


def _shared_course_id(document: dict, index: int) -> bool:
    """Whether another section has the same course id as section ``index``."""
    courses = items(document, "courses")
    course_id = courses[index]["course_id"]
    return any(
        other["course_id"] == course_id
        for position, other in enumerate(courses)
        if position != index
    )


def _references_to(document: dict, area: str, name: str):
    """Yield ``(owner_area, owner_index, field, value)`` for every reference to ``name``."""
    courses = items(document, "courses")
    faculty = items(document, "faculty")
    course_fields = {"rooms": "room", "labs": "lab", "faculty": "faculty", "courses": "conflicts"}
    faculty_fields = {
        "rooms": "room_preferences",
        "labs": "lab_preferences",
        "courses": "course_preferences",
    }
    if area in course_fields:
        key = course_fields[area]
        for position, course in enumerate(courses):
            values = course.get(key) or []
            if name in values:
                yield "courses", position, key, values
    if area in faculty_fields:
        key = faculty_fields[area]
        for position, member in enumerate(faculty):
            values = member.get(key) or {}
            if name in values:
                yield "faculty", position, key, values


def _without(values, name: str):
    if isinstance(values, dict):
        return {key: rank for key, rank in values.items() if key != name}
    return [value for value in values if value != name]


def _renamed(values, old: str, new: str):
    if isinstance(values, dict):
        return {(new if key == old else key): rank for key, rank in values.items()}
    return [new if value == old else value for value in values]
