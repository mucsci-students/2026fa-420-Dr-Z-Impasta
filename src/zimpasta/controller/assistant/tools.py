"""The actions the AI assistant can take, each one a defined tool (the Command pattern).

A :class:`Tool` pairs a name and description with a pydantic model for its arguments and a
handler that carries the action out through :class:`AppController`, the same objects the
GUI's routes use. :class:`ToolRegistry` publishes the tools to the model as function
definitions and runs the model's calls: :meth:`~ToolRegistry.dispatch` checks the
arguments, runs the handler, and always returns a :class:`ToolResult`, never an
exception, so the model and the chat transcript both see exactly what happened.

The GUI's safeguards apply:

* Every edit goes through :class:`~zimpasta.model.workspace.ConfigWorkspace`, so the
  scheduler library validates the whole configuration and a rejected edit changes nothing.
* ``edit_configuration`` applies all of a request's changes in one transaction: if any is
  rejected, none is applied.
* Deleting asks the user first, as the GUI's delete dialog does, and a delete that other
  items depend on is refused with the reason.
* Starting a new configuration over unsaved changes asks the user first.
* Saving is finished by the user in the browser (Save As, then marked saved), exactly as
  the editor's Save button does; the assistant only prepares it.

A result's ``status`` is ``done``, ``failed``, or ``waiting`` (for the user to confirm or
to finish saving). Only ``done`` means the action happened.
"""

import json
import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from scheduler import TimeSlotConfig

from zimpasta.model import catalog
from zimpasta.model import references as refs
from zimpasta.model.generation_job import GenerationBusy, InvalidOverrides
from zimpasta.model.issues import issue
from zimpasta.model.schedules import ScheduleError
from zimpasta.model.workspace import (
    ITEM_TYPES,
    DeleteBlocked,
    NoConfiguration,
    UnsavedChanges,
    WorkspaceError,
)

if TYPE_CHECKING:
    from zimpasta.controller.app_controller import AppController

logger = logging.getLogger("zimpasta.assistant")

ItemArea = Literal["rooms", "labs", "courses", "faculty", "patterns"]
EditArea = Literal["rooms", "labs", "courses", "faculty", "patterns", "time_slots", "settings"]
InspectArea = Literal[
    "overview", "rooms", "labs", "courses", "faculty", "patterns", "time_slots", "settings"
]
SECTIONS = ("time_slots", "settings")

MAX_LISTED = 200
"""The most items one inspection returns."""

MAX_CHANGES = 25
"""The most changes one edit_configuration call may make."""


# -------------------------------------------------------------------- results


@dataclass(frozen=True)
class PendingAction:
    """Something the user must do before a tool's action happens."""

    kind: Literal["confirm", "save"]
    prompt: str
    """What the user is asked, such as ``Delete room Roddy 136?``."""

    details: tuple[str, ...] = ()
    run: Callable[[], "ToolResult"] | None = None
    """For ``confirm``: carries the action out once the user confirms."""

    revision: int = 0
    """The configuration revision this was prepared for. A confirmation for an older
    revision is refused, since the configuration has changed since."""


@dataclass(frozen=True)
class ToolResult:
    """The outcome of one tool call, for the model and for the transcript."""

    status: Literal["done", "failed", "waiting"]
    summary: str
    """One sentence about what happened, shown in the chat."""

    data: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] | None = None
    pending: PendingAction | None = None

    @property
    def ok(self) -> bool:
        return self.status == "done"

    @classmethod
    def done(cls, summary: str, **data: Any) -> "ToolResult":
        return cls("done", summary, data)

    @classmethod
    def failed(
        cls, code: str, message: str, *, issues: Iterable[Mapping] = (), **extra: Any
    ) -> "ToolResult":
        error = {"code": code, "message": message, "issues": list(issues), **extra}
        return cls("failed", message, error=error)

    @classmethod
    def waiting(cls, summary: str, pending: PendingAction, **data: Any) -> "ToolResult":
        return cls("waiting", summary, data, pending=pending)

    def for_model(self) -> str:
        """The result as the model reads it: JSON text."""
        body: dict[str, Any] = {"status": self.status, "summary": self.summary, **self.data}
        if self.error is not None:
            body["error"] = self.error
        if self.pending is not None:
            body["waiting_for_user"] = {
                "kind": self.pending.kind,
                "prompt": self.pending.prompt,
                "details": list(self.pending.details),
                "note": (
                    "Nothing has been saved yet. The user saves by clicking Save in the chat."
                    if self.pending.kind == "save"
                    else "Nothing has changed yet. The user confirms or cancels in the chat."
                ),
            }
        return json.dumps(body, default=str)

    def to_dict(self) -> dict:
        """The result as the transcript shows it."""
        return {"status": self.status, "ok": self.ok, "summary": self.summary, "error": self.error}


# ------------------------------------------------------------------ arguments


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InspectArguments(_Arguments):
    area: InspectArea = Field(
        description=(
            "'overview' for the status, counts, unsaved changes, and problems; or an area "
            "to list its items with their indexes."
        )
    )


class DescribeArguments(_Arguments):
    area: EditArea = Field(description="The kind of item, or the section, to describe.")


class Change(_Arguments):
    """One change in an ``edit_configuration`` call."""

    action: Literal["add", "update", "delete"]
    area: EditArea = Field(
        description=(
            "Where the change goes. Meetings are part of a class pattern (area 'patterns'). "
            "'time_slots' and 'settings' can only be updated."
        )
    )
    index: int | None = Field(
        default=None,
        ge=0,
        description=(
            "The item's index from inspect_configuration, as it was before this call. "
            "Required to update or delete an item; leave it out otherwise."
        ),
    )
    item: dict[str, Any] | None = Field(
        default=None,
        description="add only: the complete new item, with the field names describe_fields lists.",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description=(
            "update only: just the fields to change, with their new values. A list value "
            "replaces the whole list."
        ),
    )

    @model_validator(mode="after")
    def _complete(self) -> Self:
        section = self.area in SECTIONS
        if section and self.action != "update":
            raise ValueError(f"{self.area} can only be updated")
        if self.action == "add":
            if self.item is None:
                raise ValueError(f"adding to {self.area} needs 'item', the complete new item")
            if self.index is not None or self.fields is not None:
                raise ValueError("add takes only 'item', not 'index' or 'fields'")
        elif self.action == "update":
            if not self.fields:
                raise ValueError("update needs 'fields', the fields to change")
            if not section and self.index is None:
                raise ValueError(f"updating {self.area} needs 'index', which item to change")
            if section and self.index is not None:
                raise ValueError(f"{self.area} is one section, so it takes no 'index'")
            if self.item is not None:
                raise ValueError("update takes 'fields', not 'item'")
        else:
            if self.index is None:
                raise ValueError(f"deleting from {self.area} needs 'index', which item to delete")
            if self.item is not None or self.fields is not None:
                raise ValueError("delete takes only 'index'")
        return self

    def describe(self) -> str:
        where = self.area if self.index is None else f"{self.area} #{self.index}"
        return f"{self.action} {where}"


class EditArguments(_Arguments):
    changes: list[Change] = Field(
        min_length=1,
        max_length=MAX_CHANGES,
        description=(
            "Every change for this request. They are applied together: if any is rejected, "
            "none is applied. Indexes refer to the configuration before these changes."
        ),
    )


class NoArguments(_Arguments):
    pass


class GenerateArguments(_Arguments):
    limit: int | None = Field(
        default=None,
        ge=1,
        description=(
            "This run only: how many schedules to generate. Leave out for the configured limit."
        ),
    )
    optimizer_flags: list[str] | None = Field(
        default=None,
        description=(
            "This run only: the exact optimizer flags. Leave out for the configured flags; "
            "an empty list turns optimization off."
        ),
    )


# ---------------------------------------------------------------- the registry


@dataclass(frozen=True)
class Tool:
    """One action the model may call: a command with defined arguments."""

    name: str
    description: str
    arguments: type[BaseModel]
    handler: Callable[["AppController", Any], ToolResult]

    def definition(self) -> dict[str, Any]:
        """The OpenAI function definition. Arguments are checked here, not by the API."""
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": _parameters(self.arguments),
            "strict": False,
        }


class ToolRegistry:
    """The tools the model may call, and the one place calls are run."""

    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Two tools are named {tool.name!r}.")
            self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def definitions(self) -> list[dict[str, Any]]:
        return [tool.definition() for tool in self._tools.values()]

    def dispatch(self, controller: "AppController", name: str, arguments: str) -> ToolResult:
        """Run one call from the model. Never raises: every outcome is a result."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failed(
                "unknown_tool",
                f"There is no tool named {name!r}. The tools are: {', '.join(self._tools)}.",
            )
        try:
            raw = json.loads(arguments or "{}")
        except json.JSONDecodeError as error:
            return ToolResult.failed(
                "invalid_arguments", f"The arguments for {name} aren't valid JSON: {error.msg}."
            )
        if not isinstance(raw, dict):
            return ToolResult.failed(
                "invalid_arguments", f"The arguments for {name} must be a JSON object."
            )
        try:
            parsed = tool.arguments.model_validate(raw)
        except ValidationError as error:
            problems = _argument_issues(error)
            return ToolResult.failed(
                "invalid_arguments",
                f"The request is missing or has wrong information for {name}: "
                f"{problems[0]['message']}",
                issues=problems,
            )
        try:
            return tool.handler(controller, parsed)
        except (WorkspaceError, ScheduleError, GenerationBusy, InvalidOverrides) as error:
            return _failure(error)
        except Exception:
            logger.exception("The %s tool failed unexpectedly", name)
            return ToolResult.failed(
                "tool_failed", f"Something went wrong running {name}. Nothing was changed."
            )


def _parameters(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema with references inlined and titles dropped."""
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                target = resolve(definitions[node["$ref"].rsplit("/", 1)[-1]])
                return {**target, **{k: resolve(v) for k, v in node.items() if k != "$ref"}}
            return {key: resolve(value) for key, value in node.items() if key != "title"}
        if isinstance(node, list):
            return [resolve(value) for value in node]
        return node

    return resolve(schema)


def _argument_issues(error: ValidationError) -> list[dict]:
    problems = []
    for detail in error.errors(include_url=False):
        path = ".".join(str(part) for part in detail.get("loc", ()))
        message = str(detail.get("msg", "Invalid value.")).removeprefix("Value error, ")
        if detail.get("type") == "missing":
            message = f"{path} is required"
        elif path:
            message = f"{path}: {message}"
        code = str(detail.get("type", "invalid"))
        problems.append(issue(message, code=code, path=path).to_dict())
    return problems


def _failure(error: Exception) -> ToolResult:
    code = str(getattr(error, "code", "failed"))
    message = str(getattr(error, "message", error))
    extra: dict[str, Any] = {}
    if isinstance(error, DeleteBlocked):
        extra["impact"] = error.impact.to_dict()
    if isinstance(error, UnsavedChanges):
        extra["changes"] = [change.summary for change in error.changes]
    issues = [problem.to_dict() for problem in getattr(error, "issues", ())]
    return ToolResult.failed(code, message, issues=issues, **extra)


# ------------------------------------------------------------------- handlers


def inspect_configuration(app: "AppController", args: InspectArguments) -> ToolResult:
    workspace = app.workspace
    if args.area == "overview":
        snapshot = workspace.snapshot()
        return ToolResult.done(
            "Read the configuration overview.",
            status_of_configuration=snapshot["status"],
            file=snapshot["name"],
            saved=not snapshot["dirty"],
            unsaved_changes=[change["summary"] for change in snapshot["changes"]],
            counts=snapshot["counts"],
            problems=[problem["message"] for problem in snapshot["issues"]][:20],
            generation=_brief_generation(app.generation_status()),
            schedules=app.schedules.count,
        )
    if args.area in SECTIONS:
        document = workspace.document()
        if document is None:
            raise NoConfiguration()
        if args.area == "time_slots":
            section = {k: v for k, v in document["time_slot_config"].items() if k != "classes"}
        else:
            section = {"limit": document["limit"], "optimizer_flags": document["optimizer_flags"]}
        return ToolResult.done(f"Read {args.area}.", **{args.area: section})
    listed = workspace.items(args.area)
    labels = workspace.section_labels() if args.area == "courses" else None
    entries = []
    for index, item in enumerate(listed[:MAX_LISTED]):
        entry: dict[str, Any] = {"index": index}
        if labels is not None:
            entry["section"] = labels[index]
        entries.append({**entry, **item})
    noun = refs.AREA_NOUNS[args.area]
    return ToolResult.done(
        f"Listed {len(listed)} {noun}{'' if len(listed) == 1 else 's'}.",
        area=args.area,
        items=entries,
        truncated=len(listed) > MAX_LISTED,
    )


def describe_fields(app: "AppController", args: DescribeArguments) -> ToolResult:
    options = catalog.options()
    choices = {
        "weekdays": options["weekdays"],
        "modalities": options["modalities"],
        "delivery_modes": options["delivery_modes"],
    }
    if args.area == "settings":
        schema: dict[str, Any] = {
            "limit": "a positive integer: how many schedules generation makes",
            "optimizer_flags": "a list of flag names",
        }
        choices = {"optimizer_flags": options["optimizer_flags"]}
    elif args.area == "time_slots":
        schema = TimeSlotConfig.model_json_schema()
        schema.get("properties", {}).pop("classes", None)
        if "classes" in schema.get("required", []):
            schema["required"] = [name for name in schema["required"] if name != "classes"]
    else:
        schema = ITEM_TYPES[args.area].model_json_schema()
    data: dict[str, Any] = {"area": args.area, "schema": schema, "choices": choices}
    if args.area not in SECTIONS and app.workspace.document() is not None:
        existing = app.workspace.items(args.area)
        if existing:
            data["example"] = existing[0]
    return ToolResult.done(f"Described the fields for {args.area}.", **data)


def edit_configuration(app: "AppController", args: EditArguments) -> ToolResult:
    return _apply_changes(app, args.changes, confirmed=False)


class _Rejected(Exception):
    def __init__(self, number: int, change: Change, error: WorkspaceError) -> None:
        super().__init__(error.message)
        self.number, self.change, self.error = number, change, error


class _NeedsConfirmation(Exception):
    pass


def _apply_changes(app: "AppController", changes: list[Change], *, confirmed: bool) -> ToolResult:
    """Apply every change or none. Deletes need the user's confirmation first.

    Adds and updates run in the order given; adds go at the end of their area, so the
    indexes of existing items don't move. Deletes run last, highest index first, so every
    index means what it meant before the call.
    """
    workspace = app.workspace
    numbered = list(enumerate(changes, start=1))
    deletes = [(n, c) for n, c in numbered if c.action == "delete"]
    targets = [(c.area, c.index) for _, c in deletes]
    if len(set(targets)) != len(targets):
        return ToolResult.failed(
            "invalid_arguments", "The same item is deleted twice. Nothing was changed."
        )
    ordered = [(n, c) for n, c in numbered if c.action != "delete"]
    ordered += sorted(deletes, key=lambda pair: (pair[1].area, -(pair[1].index or 0)))

    done: list[str] = []
    removals: list[str] = []
    try:
        with workspace.transaction():
            for number, change in ordered:
                try:
                    done.append(_apply_one(app, change, removals))
                except WorkspaceError as error:
                    raise _Rejected(number, change, error) from None
            if deletes and not confirmed:
                raise _NeedsConfirmation()
    except _NeedsConfirmation:
        labels = [line.removeprefix("Removed ") for line in done if line.startswith("Removed ")]
        prompt = f"Delete {', '.join(labels)}?"
        others = len(done) - len(labels)
        if others:
            prompt = prompt[:-1] + f" and apply {others} other change{'s' if others > 1 else ''}?"
        pending = PendingAction(
            kind="confirm",
            prompt=prompt,
            details=tuple(done + removals),
            run=lambda: _apply_changes(app, changes, confirmed=True),
            revision=workspace.revision,
        )
        return ToolResult.waiting(f"Waiting for confirmation: {prompt}", pending, applied=False)
    except _Rejected as rejected:
        failure = _failure(rejected.error)
        error = dict(failure.error or {})
        message = (
            f"Nothing was changed. Change {rejected.number} ({rejected.change.describe()}) "
            f"was rejected: {rejected.error.message}"
        )
        error["message"] = message
        error["change"] = rejected.number
        return ToolResult("failed", message, error=error)
    return ToolResult.done(
        _sentence(done),
        applied=True,
        changes=done + removals,
        saved_to_file=False,
        configuration=_brief_configuration(app),
    )


def _apply_one(app: "AppController", change: Change, removals: list[str]) -> str:
    workspace = app.workspace
    if change.area == "time_slots":
        return workspace.update_time_slots(change.fields or {}).summary
    if change.area == "settings":
        return workspace.update_settings(change.fields or {}).summary
    if change.action == "add":
        return workspace.add(change.area, change.item).summary
    index = change.index if change.index is not None else -1
    if change.action == "update":
        current = workspace.item(change.area, index)
        return workspace.replace(change.area, index, {**current, **(change.fields or {})}).summary
    recorded, impact = workspace.remove(change.area, index)
    for reference in impact.cascades:
        noun = refs.AREA_NOUNS.get(reference.area, reference.area)
        removals.append(
            f"Also removes {impact.label} from {noun} {reference.label} ({reference.field})"
        )
    return recorded.summary


def new_configuration(app: "AppController", args: NoArguments) -> ToolResult:
    workspace = app.workspace
    if workspace.dirty and workspace.changes:
        pending = PendingAction(
            kind="confirm",
            prompt="Discard the unsaved changes and start a new configuration?",
            details=tuple(change.summary for change in workspace.changes),
            run=lambda: _start_new(app),
            revision=workspace.revision,
        )
        return ToolResult.waiting(
            "Waiting for confirmation: the unsaved changes would be lost.", pending
        )
    return _start_new(app)


def _start_new(app: "AppController") -> ToolResult:
    app.new_configuration(discard_changes=True)
    return ToolResult.done(
        "Started a new, empty configuration. It becomes valid once it has at least one room, "
        "one course, and one faculty member.",
        configuration=_brief_configuration(app),
    )


def validate_configuration(app: "AppController", args: NoArguments) -> ToolResult:
    report = app.validate_configuration()["report"]
    problems = report["issues"]
    if report["valid"]:
        summary = "The scheduler library accepts the configuration: it is valid."
    else:
        count = len(problems)
        summary = f"The configuration is not valid yet: {count} problem{'s' * (count != 1)}."
    return ToolResult.done(
        summary,
        valid=report["valid"],
        status_of_configuration=report["status"],
        problems=problems[:20],
    )


def save_configuration(app: "AppController", args: NoArguments) -> ToolResult:
    exported = app.export_configuration()
    pending = PendingAction(
        kind="save", prompt=f"Save {exported.filename}", revision=exported.revision
    )
    return ToolResult.waiting(
        f"Ready to save {exported.filename}. Click Save to choose where to write it.",
        pending,
        filename=exported.filename,
        saved_to_file=False,
    )


def generate_schedules(app: "AppController", args: GenerateArguments) -> ToolResult:
    status = app.start_generation(limit=args.limit, optimizer_flags=args.optimizer_flags)
    return ToolResult.done(
        f"Started generating schedules. {status['message']}",
        generation=_brief_generation(status),
        note=(
            "Generation runs in the background. Progress shows in the Schedule Generator, "
            "and finished schedules appear in the Schedule Viewer."
        ),
    )


def generation_status(app: "AppController", args: NoArguments) -> ToolResult:
    status = app.generation_status()
    brief = _brief_generation(status)
    return ToolResult.done(
        status["message"] or f"Generation is {status['state']}.",
        generation=brief,
        schedules=app.schedules.count,
    )


def _brief_generation(status: Mapping[str, Any]) -> dict[str, Any]:
    settings = status.get("settings") or {}
    return {
        "state": status["state"],
        "running": status["running"],
        "found": status["found"],
        "limit": settings.get("limit"),
        "message": status["message"],
    }


def _brief_configuration(app: "AppController") -> dict[str, Any]:
    snapshot = app.workspace.snapshot()
    return {
        "status": snapshot["status"],
        "counts": snapshot["counts"],
        "unsaved_changes": len(snapshot["changes"]),
    }


def _sentence(lines: list[str]) -> str:
    if len(lines) == 1:
        return lines[0] + "."
    return f"Applied {len(lines)} changes: " + "; ".join(lines) + "."


TOOLS = ToolRegistry(
    [
        Tool(
            "inspect_configuration",
            "Read the configuration: an overview (status, counts, unsaved changes, problems), "
            "or the items of one area with their indexes, or the time_slots or settings section.",
            InspectArguments,
            inspect_configuration,
        ),
        Tool(
            "describe_fields",
            "The scheduler library's field definitions for one kind of item or section, with "
            "the allowed values and an existing example. Use it before adding or changing items.",
            DescribeArguments,
            describe_fields,
        ),
        Tool(
            "edit_configuration",
            "Add, update, or delete items (rooms, labs, courses, faculty, class patterns and "
            "their meetings) and update time_slots or settings, as one batch that is applied "
            "entirely or not at all. The scheduler library validates the result. Deletions wait "
            "for the user to confirm. Changes are in memory until the configuration is saved.",
            EditArguments,
            edit_configuration,
        ),
        Tool(
            "new_configuration",
            "Start a new, empty configuration. If there are unsaved changes, the user must "
            "confirm discarding them first.",
            NoArguments,
            new_configuration,
        ),
        Tool(
            "validate_configuration",
            "Ask the scheduler library whether the whole configuration is valid, and list its "
            "problems if not.",
            NoArguments,
            validate_configuration,
        ),
        Tool(
            "save_configuration",
            "Prepare saving the configuration as a JSON file. The user finishes it by clicking "
            "Save in the chat; it is not saved until then. The configuration must be valid.",
            NoArguments,
            save_configuration,
        ),
        Tool(
            "generate_schedules",
            "Start generating schedules from the current valid configuration, in the "
            "background. The limit and optimizer flags can be overridden for this run only.",
            GenerateArguments,
            generate_schedules,
        ),
        Tool(
            "generation_status",
            "How the current or most recent generation run is going, and how many schedules "
            "the Schedule Viewer has.",
            NoArguments,
            generation_status,
        ),
    ]
)
