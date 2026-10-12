"""Turn Model failures into consistent JSON error responses.

Every error the API returns has the same shape, so a view can show any of them the same
way::

    {"error": {"code": "edit_rejected",
               "message": "The change was not applied: ...",
               "issues": [{"path": ..., "area": ..., "index": ..., "field": ..., "message": ...}],
               ...extra fields for some codes...}}

``code`` is stable and meant for the view's logic; ``message`` is meant for the user.
Unexpected errors are logged with their traceback and reported with a friendly message
and a short reference, never a raw traceback.
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from zimpasta.model.generation_job import GenerationBusy, InvalidOverrides
from zimpasta.model.schedules import (
    InvalidScheduleFile,
    NoSchedules,
    ScheduleError,
    ScheduleNotFound,
)
from zimpasta.model.workspace import (
    DeleteBlocked,
    EditRejected,
    InvalidFile,
    ItemNotFound,
    NoConfiguration,
    NotValid,
    UnsavedChanges,
    WorkspaceError,
)

logger = logging.getLogger("zimpasta.api")

UNEXPECTED = (
    "Something unexpected went wrong. Your configuration and schedules were not changed. "
    "If it keeps happening, restart zimpasta and report reference {reference}."
)

_FILE_READ_CODES = {"malformed_json", "unreadable_file"}


def error_body(code: str, message: str, *, issues=(), **extra) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "issues": [problem.to_dict() for problem in issues],
            **extra,
        }
    }


def _respond(status: int, code: str, message: str, *, issues=(), **extra) -> JSONResponse:
    return JSONResponse(error_body(code, message, issues=issues, **extra), status_code=status)


def _status_for(error: Exception) -> int:
    match error:
        case ItemNotFound() | ScheduleNotFound():
            return 404
        case NoConfiguration() | UnsavedChanges() | DeleteBlocked() | NotValid() | NoSchedules():
            return 409
        case GenerationBusy():
            return 409
        case InvalidFile() | InvalidScheduleFile() if error.code in _FILE_READ_CODES:
            return 400
        case InvalidFile() | InvalidScheduleFile() | EditRejected() | InvalidOverrides():
            return 422
        case _:
            return 400


async def _model_error(request: Request, error: Exception) -> JSONResponse:
    extra = {}
    if isinstance(error, UnsavedChanges):
        extra["changes"] = [change.to_dict() for change in error.changes]
    if isinstance(error, DeleteBlocked):
        extra["impact"] = error.impact.to_dict()
    return _respond(
        _status_for(error),
        error.code,
        error.message,
        issues=getattr(error, "issues", ()),
        **extra,
    )


async def _bad_request(request: Request, error: RequestValidationError) -> JSONResponse:
    details = [
        {
            "location": ".".join(str(part) for part in detail.get("loc", ())),
            "message": detail.get("msg", "Invalid value."),
        }
        for detail in error.errors()
    ]
    first = details[0]["message"] if details else "Invalid request."
    return _respond(400, "bad_request", f"The request was not understood: {first}", details=details)


async def _http_error(request: Request, error: HTTPException) -> JSONResponse:
    code = "not_found" if error.status_code == 404 else "http_error"
    message = "There is no such API endpoint." if error.status_code == 404 else str(error.detail)
    return _respond(error.status_code, code, message)


async def _unexpected(request: Request, error: Exception) -> JSONResponse:
    reference = uuid.uuid4().hex[:8]
    logger.exception("Unexpected error %s handling %s %s", reference, request.method, request.url)
    return _respond(500, "unexpected", UNEXPECTED.format(reference=reference), reference=reference)


def install(app: FastAPI) -> None:
    """Register every handler on ``app``."""
    for error_type in (WorkspaceError, ScheduleError, GenerationBusy, InvalidOverrides):
        app.add_exception_handler(error_type, _model_error)
    app.add_exception_handler(RequestValidationError, _bad_request)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected)
