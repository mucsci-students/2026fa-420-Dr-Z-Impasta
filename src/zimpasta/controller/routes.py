"""The HTTP API under ``/api``. Each route is a thin wrapper around one controller method.

Routes only translate HTTP into a call on :class:`AppController` and back. Request bodies
that carry configuration items are passed through as plain JSON objects: the Model
validates them with the scheduler library, so its located issues reach the view instead
of FastAPI's generic messages.

Specific paths (``/config/schema``, ``/config/time-slots``, ...) are declared before the
``/config/{area}`` routes so they are matched first.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field

from zimpasta.controller.app_controller import AppController

router = APIRouter(prefix="/api")

JsonObject = Annotated[dict[str, Any], Body()]
"""A configuration item or section, validated by the Model rather than by FastAPI."""


def controller(request: Request) -> AppController:
    return request.app.state.controller


App = Annotated[AppController, Depends(controller)]


class DiscardRequest(BaseModel):
    discard_changes: bool = False
    """Replace the configuration even though it has unsaved changes."""


class LoadRequest(DiscardRequest):
    filename: str = Field(min_length=1, max_length=255)
    content: str
    """The file's text, as read by the browser."""


class SavedRequest(BaseModel):
    revision: int = Field(ge=0)
    """The revision that was exported and written to disk."""

    filename: str | None = Field(default=None, max_length=255)


class GenerateRequest(BaseModel):
    limit: Any = None
    """Override for this run only. Omit or ``null`` to use the configured limit."""

    optimizer_flags: Any = None
    """Override for this run only: the exact list of flags. Omit for the configured flags."""


class ImportRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str


def _download(content: str, filename: str, media_type: str, **headers: str) -> Response:
    return Response(
        content=content.encode("utf-8"),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', **headers},
    )


# ------------------------------------------------------------------- state


@router.get("/state")
def get_state(app: App) -> dict:
    """Configuration status, generation status, and schedule counts, for the header."""
    return app.state()


# ----------------------------------------------------------- configuration


@router.get("/config")
def get_configuration(app: App) -> dict:
    return app.configuration()


@router.get("/config/schema")
def get_schema(app: App) -> dict:
    """The scheduler library's JSON Schema for a complete configuration."""
    return app.schema()


@router.get("/config/options")
def get_options(app: App) -> dict:
    """Weekdays, modalities, delivery modes, and optimizer flags with descriptions."""
    return app.options()


@router.post("/config/new")
def new_configuration(app: App, request: DiscardRequest | None = None) -> dict:
    discard = request.discard_changes if request else False
    return app.new_configuration(discard_changes=discard)


@router.post("/config/load")
def load_configuration(app: App, request: LoadRequest) -> dict:
    return app.load_configuration(
        request.filename, request.content, discard_changes=request.discard_changes
    )


@router.post("/config/validate")
def validate_configuration(app: App) -> dict:
    return app.validate_configuration()


@router.get("/config/export")
def export_configuration(app: App) -> Response:
    """The configuration as a JSON file. Its revision is in ``X-Config-Revision``."""
    exported = app.export_configuration()
    return _download(
        exported.content,
        exported.filename,
        "application/json",
        **{"X-Config-Revision": str(exported.revision)},
    )


@router.post("/config/saved")
def configuration_saved(app: App, request: SavedRequest) -> dict:
    """The view wrote the exported file; mark that revision as saved."""
    return app.mark_configuration_saved(request.revision, request.filename)


@router.put("/config/time-slots")
def update_time_slots(app: App, values: JsonObject) -> dict:
    """Change ``times``, ``max_time_gap``, and/or ``min_time_overlap``."""
    return app.update_time_slots(values)


@router.put("/config/settings")
def update_settings(app: App, values: JsonObject) -> dict:
    """Change the configured ``limit`` and/or ``optimizer_flags``."""
    return app.update_settings(values)


@router.get("/config/{area}")
def list_items(app: App, area: str) -> dict:
    return app.list_items(area)


@router.post("/config/{area}", status_code=status.HTTP_201_CREATED)
def add_item(app: App, area: str, item: JsonObject) -> dict:
    return app.add_item(area, item)


@router.get("/config/{area}/{index}")
def get_item(app: App, area: str, index: int) -> dict:
    return app.get_item(area, index)


@router.put("/config/{area}/{index}")
def replace_item(app: App, area: str, index: int, item: JsonObject) -> dict:
    return app.replace_item(area, index, item)


@router.get("/config/{area}/{index}/impact")
def delete_impact(app: App, area: str, index: int) -> dict:
    """What deleting the item would block, remove, or break. Changes nothing."""
    return app.delete_impact(area, index)


@router.delete("/config/{area}/{index}")
def delete_item(app: App, area: str, index: int) -> dict:
    return app.delete_item(area, index)


# -------------------------------------------------------------- generation


@router.get("/generation")
def generation_status(app: App) -> dict:
    return app.generation_status()


@router.post("/generation", status_code=status.HTTP_202_ACCEPTED)
def start_generation(app: App, request: GenerateRequest | None = None) -> dict:
    request = request or GenerateRequest()
    return app.start_generation(limit=request.limit, optimizer_flags=request.optimizer_flags)


@router.post("/generation/cancel")
def cancel_generation(app: App) -> dict:
    return app.cancel_generation()


# --------------------------------------------------------------- schedules


@router.get("/schedules")
def schedule_summary(app: App) -> dict:
    return app.schedule_summary()


@router.get("/schedules/export")
def export_schedules(
    app: App,
    format: Literal["json", "csv"] = "json",
    which: Annotated[str, Query(pattern=r"^(all|[1-9][0-9]*)$")] = "all",
) -> Response:
    exported = app.export_schedules("all" if which == "all" else int(which), format)
    return _download(exported.content, exported.filename, exported.media_type)


@router.post("/schedules/import")
def import_schedules(app: App, request: ImportRequest) -> dict:
    return app.import_schedules(request.filename, request.content)


@router.delete("/schedules")
def clear_schedules(app: App) -> dict:
    return app.clear_schedules()


@router.get("/schedules/{number}")
def schedule_view(app: App, number: int, group: Literal["room", "faculty"] = "room") -> dict:
    """One schedule, grouped by room and lab or by faculty member."""
    return app.schedule_view(number, group)
