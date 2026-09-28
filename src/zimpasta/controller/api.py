"""Build the FastAPI application that serves the API (and, later, the built GUI)."""

from collections.abc import Iterable

from fastapi import FastAPI

from zimpasta.controller import errors, security
from zimpasta.controller.app_controller import AppController
from zimpasta.controller.routes import router


def create_app(
    controller: AppController | None = None,
    *,
    allowed_hosts: Iterable[str] = security.DEFAULT_ALLOWED_HOSTS,
) -> FastAPI:
    """A FastAPI app around ``controller`` (a fresh one if not given).

    One application object serves one user's session: the controller holds the
    configuration and schedules in memory for as long as the server runs.
    """
    app = FastAPI(
        title="Dr. ZImpasta",
        summary="Configuration editor, schedule generator, and schedule viewer API.",
        version="0.2.0",
    )
    app.state.controller = controller or AppController()
    errors.install(app)
    security.install(app, allowed_hosts)
    app.include_router(router)
    return app
