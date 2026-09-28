"""``zimpasta --gui``: run the graphical interface as a local web app.

One process serves both the API and the built React GUI on ``127.0.0.1`` and, unless
told not to, opens the default browser on it. The configuration and schedules live in
this process's memory; closing the browser tab keeps them, stopping the server (Ctrl+C)
ends the session. Files are opened and saved through the browser.
"""

import os
import socket
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from zimpasta.controller import AppController, create_app
from zimpasta.controller import static as static_files
from zimpasta.model.generate import quiet_library_logging
from zimpasta.model.workspace import WorkspaceError

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_ATTEMPTS = 20
"""Without ``--port``, try this many ports from ``DEFAULT_PORT`` up."""


class PortUnavailable(Exception):
    pass


def create_gui_app(
    controller: AppController | None = None, *, static_dir: Path | None = static_files.BUILT_GUI
) -> FastAPI:
    """The API plus the built GUI, in one FastAPI application."""
    app = create_app(controller)
    static_files.install(app, static_dir)
    return app


def port_is_free(port: int, host: str = HOST) -> bool:
    """Whether uvicorn could listen on ``port`` right now.

    Like uvicorn, the probe sets ``SO_REUSEADDR`` (except on Windows, where it would let
    two servers share a port), so a port whose last server just stopped counts as free.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name != "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
        return True


def choose_port(requested: int | None, *, is_free: Callable[[int], bool] = port_is_free) -> int:
    """``requested`` if it is free; without a request, the first free port from 8000 up.

    Raises:
        PortUnavailable: with a message saying what to do.
    """
    if requested is not None:
        if not 1 <= requested <= 65535:
            raise PortUnavailable(f"Port {requested} is not a valid port number (1-65535).")
        if not is_free(requested):
            raise PortUnavailable(
                f"Port {requested} is already in use. Stop whatever is using it, or choose "
                "another with --port."
            )
        return requested
    for port in range(DEFAULT_PORT, DEFAULT_PORT + PORT_ATTEMPTS):
        if is_free(port):
            return port
    raise PortUnavailable(
        f"Ports {DEFAULT_PORT}-{DEFAULT_PORT + PORT_ATTEMPTS - 1} are all in use. "
        "Choose a free one with --port."
    )


def serve(
    *,
    config: str | Path | None = None,
    port: int | None = None,
    open_browser: bool = True,
    static_dir: Path | None = static_files.BUILT_GUI,
    say: Callable[[str], None] = print,
    run: Callable[[uvicorn.Server], None] = lambda server: server.run(),
) -> int:
    """Start the GUI server and block until it stops. Returns a process exit code."""
    quiet_library_logging()
    controller = AppController()
    if config is not None:
        try:
            controller.load_configuration_file(config)
        except WorkspaceError as error:
            say(f"Can't open {config}: {error.message}")
            for problem in error.issues[:10]:
                where = f"{problem.path}: " if problem.path else ""
                say(f"  - {where}{problem.message}")
            return 2
    try:
        chosen = choose_port(port)
    except PortUnavailable as error:
        say(str(error))
        return 1

    url = f"http://{HOST}:{chosen}/"
    server = uvicorn.Server(
        uvicorn.Config(
            create_gui_app(controller, static_dir=static_dir),
            host=HOST,
            port=chosen,
            log_level="warning",
        )
    )
    if static_dir is None or not (static_dir / "index.html").is_file():
        say("The GUI hasn't been built yet: run `npm ci` and `npm run build` in frontend/.")
    say(f"Dr. ZImpasta is running at {url}")
    say("Press Ctrl+C to stop.")
    if open_browser:
        threading.Thread(
            target=_open_when_ready, args=(server, url), name="zimpasta-browser", daemon=True
        ).start()
    run(server)
    return 0


def _open_when_ready(server: uvicorn.Server, url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if server.started:
        webbrowser.open(url)
