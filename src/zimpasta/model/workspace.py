"""The configuration workspace: the one scheduler configuration the GUI works on.

The workspace holds a ``CombinedConfig`` JSON document and applies every change as a
transaction: build the changed document, validate the *whole* document with the
scheduler library, and commit only if the library accepts it. A rejected change leaves
the stored configuration exactly as it was and reports the library's problems as
:class:`~zimpasta.model.issues.Issue` records.

Status
------
``none``
    Nothing has been created or loaded.
``incomplete``
    Created with :meth:`ConfigWorkspace.new` and still missing a room, a course, or a
    faculty member, which the library requires. The only problems tolerated are those
    "add at least one ..." messages; every other rule the library can check is enforced
    on every edit. The library checks names and references across items only once all
    three lists have an entry, so those checks run on the edit that completes the
    configuration. An incomplete configuration cannot be saved or used for generation.
``valid``
    The library accepts the whole configuration. From here an edit is committed only if
    the result is still valid, so a valid configuration never becomes invalid.

Unsaved changes
---------------
Each committed change bumps ``revision`` and adds a :class:`Change` to a journal.
``mark_saved`` records which revision the user saved; ``dirty`` is true while newer
changes exist. ``new`` and ``load_text`` refuse to discard unsaved changes unless called
with ``discard_changes=True``, raising :class:`UnsavedChanges` with the journal so the
view can list what would be lost.

Items are addressed by area (``rooms``, ``labs``, ``courses``, ``faculty``,
``patterns``) and position, because course ids repeat across sections.
"""

import copy
import dataclasses
import json
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError
from scheduler import (
    CombinedConfig,
    CourseConfig,
    FacultyConfig,
    LabConfig,
    RoomConfig,
    TimeSlotConfig,
)
from scheduler.config import ClassPattern

from zimpasta.model import references as refs
from zimpasta.model.defaults import empty_configuration
from zimpasta.model.issues import COLLECTIONS, Issue, issue, issues_from_error

AREAS: tuple[str, ...] = tuple(COLLECTIONS)
"""Editable item lists, in the order the editor shows them."""

ITEM_TYPES = {
    "rooms": RoomConfig,
    "labs": LabConfig,
    "courses": CourseConfig,
    "faculty": FacultyConfig,
    "patterns": ClassPattern,
}
"""The library type each area's items must satisfy."""

TIME_SLOT_FIELDS = ("times", "max_time_gap", "min_time_overlap")
"""``time_slot_config`` fields edited as one section; class patterns are their own area."""

SETTINGS_FIELDS = ("limit", "optimizer_flags")

DEFAULT_FILENAME = "configuration.json"

_SUMMARY_FIELDS = 3
"""How many changed fields an edit summary names before saying "and N more"."""


class ConfigStatus(StrEnum):
    NONE = "none"
    INCOMPLETE = "incomplete"
    VALID = "valid"


class WorkspaceError(Exception):
    """Base class for every expected workspace failure. ``message`` is user-facing."""

    code = "workspace_error"

    def __init__(self, message: str, *, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message)
        self.message = message
        self.issues = tuple(issues)


class NoConfiguration(WorkspaceError):
    code = "no_configuration"

    def __init__(self) -> None:
        super().__init__("No configuration is open. Create a new one or load a JSON file.")


class ItemNotFound(WorkspaceError):
    code = "not_found"


class UnsavedChanges(WorkspaceError):
    code = "unsaved_changes"

    def __init__(self, changes: tuple["Change", ...]) -> None:
        count = len(changes)
        noun = "change has" if count == 1 else "changes have"
        super().__init__(f"{count} {noun} not been saved and would be lost.")
        self.changes = changes


class InvalidFile(WorkspaceError):
    """A configuration file could not be read, parsed, or validated. Nothing was changed."""

    def __init__(self, code: str, message: str, *, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message, issues=issues)
        self.code = code


class EditRejected(WorkspaceError):
    code = "edit_rejected"


class DeleteBlocked(WorkspaceError):
    code = "delete_blocked"

    def __init__(self, impact: refs.DeleteImpact) -> None:
        if impact.blocking:
            count = len(impact.blocking)
            noun = "section depends" if count == 1 else "sections depend"
            message = f"Can't delete {impact.label}: {count} {noun} on it."
        else:
            message = f"Can't delete {impact.label}: the configuration would no longer be valid."
        super().__init__(message, issues=impact.problems)
        self.impact = impact


class NotValid(WorkspaceError):
    code = "configuration_incomplete"

    def __init__(self, issues: tuple[Issue, ...]) -> None:
        super().__init__(
            "The configuration is not complete yet. " + " ".join(i.message for i in issues),
            issues=issues,
        )


@dataclass(frozen=True)
class Change:
    """One committed change, for the unsaved-changes list."""

    revision: int
    action: str
    """``added``, ``edited``, ``removed``, or ``updated``."""

    area: str
    """An item area, ``time_slots``, or ``settings``."""

    summary: str
    """For example ``Faculty Hardy: maximum_credits 14 → 12``."""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    status: ConfigStatus
    issues: tuple[Issue, ...]
    checked_at: datetime

    @property
    def valid(self) -> bool:
        return self.status is ConfigStatus.VALID

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "valid": self.valid,
            "issues": [problem.to_dict() for problem in self.issues],
            "checked_at": self.checked_at.isoformat(timespec="seconds"),
        }


@dataclass(frozen=True)
class ExportedConfig:
    content: str
    filename: str
    revision: int


@dataclass(frozen=True)
class _Evaluation:
    status: ConfigStatus | None
    """``None`` when the library rejects the document outright."""

    config: CombinedConfig | None
    issues: tuple[Issue, ...]
    document: dict | None
    """The document in the library's canonical JSON form, when acceptable."""


class ConfigWorkspace:
    """The configuration being edited, with transactional, library-validated changes."""

    def __init__(self, *, clock: Callable[[], datetime] = datetime.now) -> None:
        self._lock = threading.RLock()
        self._clock = clock
        self._status = ConfigStatus.NONE
        self._document: dict | None = None
        self._config: CombinedConfig | None = None
        self._issues: tuple[Issue, ...] = ()
        self._name: str | None = None
        self._revision = 0
        self._saved_revision = 0
        self._changes: list[Change] = []
        self._validated_at: datetime | None = None

    # ------------------------------------------------------------------ reading

    @property
    def status(self) -> ConfigStatus:
        return self._status

    @property
    def name(self) -> str | None:
        """The file name the configuration was loaded from or last saved as."""
        return self._name

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def dirty(self) -> bool:
        return self._revision != self._saved_revision

    @property
    def changes(self) -> tuple[Change, ...]:
        return tuple(self._changes)

    @property
    def config(self) -> CombinedConfig | None:
        """The validated library object, or ``None`` unless the status is ``valid``."""
        return self._config

    @property
    def issues(self) -> tuple[Issue, ...]:
        """What keeps an incomplete configuration from being valid; empty otherwise."""
        return self._issues

    def document(self) -> dict | None:
        """A copy of the configuration as a ``CombinedConfig`` JSON document."""
        with self._lock:
            return copy.deepcopy(self._document)

    def items(self, area: str) -> list[dict]:
        with self._lock:
            return copy.deepcopy(refs.items(self._require_document(), self._area(area)))

    def item(self, area: str, index: int) -> dict:
        with self._lock:
            return copy.deepcopy(self._item(self._require_document(), area, index))

    def section_labels(self) -> list[str]:
        """``CMSC 140.01``-style labels for the course sections, in order."""
        with self._lock:
            if self._document is None:
                return []
            return refs.section_labels(refs.items(self._document, "courses"))

    def counts(self) -> dict[str, int]:
        with self._lock:
            if self._document is None:
                return {}
            doc = self._document
            courses = refs.items(doc, "courses")
            patterns = refs.items(doc, "patterns")
            return {
                "rooms": len(refs.items(doc, "rooms")),
                "labs": len(refs.items(doc, "labs")),
                "sections": len(courses),
                "courses": len({course["course_id"] for course in courses}),
                "faculty": len(refs.items(doc, "faculty")),
                "patterns": len(patterns),
                "enabled_patterns": sum(not pattern.get("disabled") for pattern in patterns),
            }

    def snapshot(self) -> dict:
        """Everything a view needs to show the configuration's state (not its contents)."""
        with self._lock:
            return {
                "status": self._status.value,
                "name": self._name,
                "revision": self._revision,
                "saved_revision": self._saved_revision,
                "dirty": self.dirty,
                "changes": [change.to_dict() for change in self._changes],
                "issues": [problem.to_dict() for problem in self._issues],
                "validated_at": (
                    self._validated_at.isoformat(timespec="seconds") if self._validated_at else None
                ),
                "counts": self.counts(),
            }

    # ---------------------------------------------------------------- lifecycle

    def new(self, *, discard_changes: bool = False) -> None:
        """Start an empty configuration with default time slots and class patterns."""
        with self._lock:
            self._guard_unsaved(discard_changes)
            evaluation = self._evaluate(empty_configuration())
            if evaluation.status is not ConfigStatus.INCOMPLETE:
                raise RuntimeError("The default configuration is not acceptable to the library.")
            self._reset(evaluation, name=None)

    def load_text(self, text: str, *, filename: str, discard_changes: bool = False) -> None:
        """Replace the configuration with a JSON document, if the library accepts it.

        The file is parsed and validated before anything else happens, so a bad file is
        reported without asking about unsaved changes.

        Raises:
            InvalidFile: the text is not JSON, not an object, or not a valid configuration.
            UnsavedChanges: the file is fine but unsaved changes would be lost.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidFile(
                "malformed_json",
                f"{filename} is not valid JSON: {error.msg} "
                f"(line {error.lineno}, column {error.colno}).",
            ) from None
        if not isinstance(data, dict):
            raise InvalidFile(
                "invalid_configuration",
                f"{filename} does not contain a configuration: expected a JSON object.",
            )
        evaluation = self._evaluate(data)
        if evaluation.status is not ConfigStatus.VALID:
            count = len(evaluation.issues)
            raise InvalidFile(
                "invalid_configuration",
                f"{filename} is not a valid configuration: {count} "
                f"{'problem' if count == 1 else 'problems'} found.",
                issues=evaluation.issues,
            )
        with self._lock:
            self._guard_unsaved(discard_changes)
            self._reset(evaluation, name=filename)

    def load_file(self, path: str | Path, *, discard_changes: bool = False) -> None:
        """Read ``path`` as UTF-8 and load it. Used when the GUI starts with a file."""
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            reason = error.strerror if isinstance(error, OSError) else "not UTF-8 text"
            raise InvalidFile("unreadable_file", f"Can't read {path.name}: {reason}.") from None
        self.load_text(text, filename=path.name, discard_changes=discard_changes)

    def load_empty(self, discard_changes: bool = False) -> None:

        empty_config_path = Path(__file__).parent / "new_config.json"
        with open(empty_config_path) as f:
            empty_data_str = f.read()

        empty_data = json.loads(empty_data_str)

        filename = "unnamed.json"
        evaluation = self._evaluate(empty_data)

        with self._lock:
            self._guard_unsaved(discard_changes)
            self._reset(evaluation, name=filename)

    def validate(self) -> ValidationReport:
        """Validate the whole configuration with the library now."""
        with self._lock:
            evaluation = self._evaluate(self._require_document())
            self._validated_at = self._clock()
            return ValidationReport(
                evaluation.status or ConfigStatus.INCOMPLETE,
                evaluation.issues,
                self._validated_at,
            )

    def require_valid(self) -> CombinedConfig:
        """The validated configuration, for saving and generation."""
        with self._lock:
            if self._status is ConfigStatus.NONE:
                raise NoConfiguration()
            if self._config is None:
                raise NotValid(self._issues)
            return self._config

    def export_text(self) -> ExportedConfig:
        """The configuration serialized by the library, ready to be written as UTF-8 JSON."""
        with self._lock:
            config = self.require_valid()
            return ExportedConfig(
                content=config.model_dump_json(indent=2) + "\n",
                filename=self._name or DEFAULT_FILENAME,
                revision=self._revision,
            )

    def mark_saved(self, revision: int, filename: str | None = None) -> None:
        """Record that the user saved the configuration as it was at ``revision``."""
        with self._lock:
            self._require_document()
            if not 0 <= revision <= self._revision:
                raise WorkspaceError(f"Revision {revision} does not exist.")
            self._saved_revision = max(self._saved_revision, revision)
            self._changes = [change for change in self._changes if change.revision > revision]
            if filename:
                self._name = filename

    # ------------------------------------------------------------------ editing

    def add(self, area: str, item: object) -> Change:
        """Append a new item to ``area``."""
        with self._lock:
            candidate = copy.deepcopy(self._require_document())
            listed = refs.items(candidate, self._area(area))
            listed.append(self._object(item))
            index = len(listed) - 1
            return self._commit(
                candidate,
                lambda doc: ("added", area, f"Added {self._noun(area, doc, index)}"),
            )

    def replace(self, area: str, index: int, item: object) -> Change:
        """Replace item ``index`` of ``area``. A new name also renames references to it."""
        with self._lock:
            document = self._require_document()
            old = self._item(document, area, index)
            new = self._object(item)
            candidate = copy.deepcopy(document)
            refs.items(candidate, area)[index] = new
            renamed = self._propagate_rename(candidate, area, index, old, new)
            candidate = renamed[0]

            def describe(doc: dict) -> tuple[str, str, str]:
                current = refs.items(doc, area)[index]
                noun = self._noun(area, doc, index)
                summary = f"{noun[:1].upper()}{noun[1:]}: {_diff(old, current)}"
                if renamed[1]:
                    count = renamed[1]
                    summary += f" ({count} {'reference' if count == 1 else 'references'} updated)"
                return "edited", area, summary

            return self._commit(candidate, describe)

    def delete_impact(self, area: str, index: int) -> refs.DeleteImpact:
        """What deleting item ``index`` of ``area`` would block, remove, or break."""
        with self._lock:
            document = self._require_document()
            self._item(document, area, index)
            impact = refs.delete_impact(document, area, index)
            if impact.blocking:
                return impact
            evaluation = self._evaluate(refs.apply_delete(document, area, index))
            if not self._acceptable(evaluation.status):
                impact = dataclasses.replace(impact, problems=self._blocking(evaluation.issues))
            return impact

    def remove(self, area: str, index: int) -> tuple[Change, refs.DeleteImpact]:
        """Delete item ``index`` of ``area`` and its optional references, if nothing blocks it."""
        with self._lock:
            impact = self.delete_impact(area, index)
            if not impact.can_delete:
                raise DeleteBlocked(impact)
            candidate = refs.apply_delete(self._require_document(), area, index)
            summary = f"Removed {refs.AREA_NOUNS[area]} {impact.label}"
            if impact.cascades:
                count = len(impact.cascades)
                summary += f" and {count} {'reference' if count == 1 else 'references'} to it"
            change = self._commit(candidate, lambda doc: ("removed", area, summary))
            return change, impact

    def update_time_slots(self, values: Mapping[str, object]) -> Change:
        """Change the weekday time blocks and global timing options."""
        return self._update_section("time_slot_config", "time_slots", TIME_SLOT_FIELDS, values)

    def update_settings(self, values: Mapping[str, object]) -> Change:
        """Change the generation limit and optimizer flags."""
        return self._update_section(None, "settings", SETTINGS_FIELDS, values)

    # ---------------------------------------------------------------- internals

    def _update_section(self, section, area, allowed, values) -> Change:
        with self._lock:
            values = self._object(values)
            unknown = sorted(set(values) - set(allowed))
            if unknown:
                raise EditRejected(
                    f"Unknown field: {', '.join(unknown)}.",
                    issues=tuple(
                        issue(f"{name} can't be changed here.", code="unknown_field", area=area)
                        for name in unknown
                    ),
                )
            document = self._require_document()
            candidate = copy.deepcopy(document)
            target = candidate[section] if section else candidate
            before = {name: target.get(name) for name in values}
            target.update(copy.deepcopy(values))
            noun = "Time slots" if area == "time_slots" else "Settings"
            return self._commit(
                candidate,
                lambda doc: ("updated", area, f"{noun}: {_diff(before, {**before, **values})}"),
            )

    def _commit(self, candidate: dict, describe) -> Change:
        evaluation = self._evaluate(candidate)
        if not self._acceptable(evaluation.status):
            issues = self._blocking(evaluation.issues)
            raise EditRejected(_rejection_message(issues), issues=issues)
        action, area, summary = describe(evaluation.document)
        self._revision += 1
        self._apply(evaluation)
        change = Change(self._revision, action, area, summary)
        self._changes.append(change)
        return change

    def _blocking(self, issues: tuple[Issue, ...]) -> tuple[Issue, ...]:
        """The problems that caused a rejection, without an incomplete configuration's
        standing "add at least one ..." notes, which are not the edit's fault."""
        if self._status is not ConfigStatus.INCOMPLETE:
            return issues
        causes = tuple(problem for problem in issues if not problem.is_missing_required_item)
        return causes or issues

    def _acceptable(self, status: ConfigStatus | None) -> bool:
        if status is ConfigStatus.VALID:
            return True
        return status is ConfigStatus.INCOMPLETE and self._status is ConfigStatus.INCOMPLETE

    def _evaluate(self, document: dict) -> _Evaluation:
        try:
            config = CombinedConfig.model_validate(document)
        except ValidationError as error:
            issues = tuple(issues_from_error(error))
            if issues and all(problem.is_missing_required_item for problem in issues):
                return _Evaluation(ConfigStatus.INCOMPLETE, None, issues, _canonical(document))
            return _Evaluation(None, None, issues, None)
        return _Evaluation(ConfigStatus.VALID, config, (), json.loads(config.model_dump_json()))

    def _reset(self, evaluation: _Evaluation, *, name: str | None) -> None:
        self._revision += 1
        self._saved_revision = self._revision
        self._changes = []
        self._name = name
        self._apply(evaluation)

    def _apply(self, evaluation: _Evaluation) -> None:
        self._status = evaluation.status
        self._document = evaluation.document
        self._config = evaluation.config
        self._issues = evaluation.issues
        self._validated_at = self._clock()

    def _guard_unsaved(self, discard_changes: bool) -> None:
        if self.dirty and self._changes and not discard_changes:
            raise UnsavedChanges(tuple(self._changes))

    def _require_document(self) -> dict:
        if self._document is None:
            raise NoConfiguration()
        return self._document

    def _area(self, area: str) -> str:
        if area not in COLLECTIONS:
            raise ItemNotFound(f"Unknown area {area!r}. Use one of: {', '.join(AREAS)}.")
        return area

    def _item(self, document: dict, area: str, index: int) -> dict:
        listed = refs.items(document, self._area(area))
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(listed):
            raise ItemNotFound(f"There is no {refs.AREA_NOUNS[area]} number {index}.")
        return listed[index]

    def _object(self, value: object) -> dict:
        if not isinstance(value, Mapping):
            raise EditRejected(
                "Expected a JSON object.", issues=(issue("Expected a JSON object.", code="type"),)
            )
        return copy.deepcopy(dict(value))

    def _noun(self, area: str, document: dict, index: int) -> str:
        return f"{refs.AREA_NOUNS[area]} {refs.item_label(document, area, index)}"

    def _propagate_rename(self, candidate, area, index, old, new) -> tuple[dict, int]:
        key = refs.NAME_FIELDS.get(area)
        if key is None:
            return candidate, 0
        before, after = old.get(key), new.get(key)
        if not isinstance(before, str) or not isinstance(after, str) or before == after:
            return candidate, 0
        if area == "courses" and any(
            course["course_id"] == before
            for position, course in enumerate(refs.items(candidate, "courses"))
            if position != index
        ):
            return candidate, 0
        return refs.apply_rename(candidate, area, before, after)


def _canonical(document: dict) -> dict:
    """An incomplete document with every item in the library's canonical JSON form."""
    result = copy.deepcopy(document)
    for area, item_type in ITEM_TYPES.items():
        listed = refs.items(result, area)
        listed[:] = [
            json.loads(item_type.model_validate(item).model_dump_json()) for item in listed
        ]
    result["time_slot_config"] = json.loads(
        TimeSlotConfig.model_validate(result["time_slot_config"]).model_dump_json()
    )
    return result


def _rejection_message(issues: tuple[Issue, ...]) -> str:
    if not issues:
        return "The change was not applied."
    count = len(issues)
    first = issues[0].message
    more = f" ({count - 1} more {'problem' if count == 2 else 'problems'})" if count > 1 else ""
    return f"The change was not applied: {first}{more}"


def _diff(old: Mapping, new: Mapping) -> str:
    """``maximum_credits 14 → 12, times changed`` for the fields that differ."""
    changed = [key for key in dict.fromkeys([*old, *new]) if old.get(key) != new.get(key)]
    if not changed:
        return "no changes"
    parts = []
    for key in changed[:_SUMMARY_FIELDS]:
        before, after = old.get(key), new.get(key)
        if _scalar(before) and _scalar(after):
            parts.append(f"{key} {_show(before)} → {_show(after)}")
        else:
            parts.append(f"{key} changed")
    if len(changed) > _SUMMARY_FIELDS:
        parts.append(f"and {len(changed) - _SUMMARY_FIELDS} more")
    return ", ".join(parts)


def _scalar(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _show(value: object) -> str:
    return "none" if value is None else str(value)
