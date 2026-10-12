"""The browser version: the Controller and Model running on Pyodide, with no server.

The hosted GUI (Cloudflare Pages) has no Python server. A Web Worker in the page loads
Pyodide (Python compiled to WebAssembly), writes this package into Pyodide's file system,
runs :func:`install` and :func:`start`, and then passes every API request to
:func:`handle`. That calls the same FastAPI application ``zimpasta --gui`` serves, in
process, so every route, rule, and error message behaves the same. See docs/gui.md.

Pyodide has no threads, which changes two things:

* FastAPI runs plain ``def`` endpoints on a thread pool; :func:`start` makes them run
  inline instead. Requests are answered one at a time, so nothing else changes.
* Generation runs on the event loop
  (:class:`~zimpasta.model.generation_job.EventLoopRunner`) and is limited to
  :data:`MAX_SCHEDULES` per run, since the page's Python is busy while it solves.

Nothing else imports this module, and importing it loads nothing else: the worker reads
:data:`REQUIREMENTS` before they are installed.
"""

import asyncio
import json
from typing import Any
from urllib.parse import unquote

MAX_SCHEDULES = 5
"""The most schedules one run generates in the browser."""

REQUIREMENTS = ("z3-solver==5.1.0.0", "bidict==0.24.1", "click==8.5.0")
"""Installed from PyPI. z3-solver publishes a WebAssembly build for this Pyodide version;
pydantic and FastAPI come with Pyodide. The pins match uv.lock (tests/test_browser.py)."""

WITHOUT_DEPENDENCIES = ("course-constraint-scheduler==3.0.0",)
"""Installed without dependencies: the library also requires ``uvicorn[standard]`` for its
own server, which has no WebAssembly build and isn't used here."""

_app = None


async def install() -> None:
    """Install :data:`REQUIREMENTS` into Pyodide."""
    import micropip  # only exists on Pyodide

    await micropip.install(list(REQUIREMENTS))
    await micropip.install(list(WITHOUT_DEPENDENCIES), deps=False)


def start() -> None:
    """Create the application that :func:`handle` calls. Run once, after :func:`install`."""
    global _app
    import anyio.to_thread

    anyio.to_thread.run_sync = run_inline
    _app = create_browser_app()


def create_browser_app():
    """The web API with generation on the event loop and capped at :data:`MAX_SCHEDULES`."""
    from zimpasta.controller import AppController, create_app
    from zimpasta.model.generation_job import EventLoopRunner

    return create_app(AppController(runner=EventLoopRunner(), max_schedules=MAX_SCHEDULES))


async def run_inline(func, *args, **_options):
    """Stands in for ``anyio.to_thread.run_sync``: call ``func`` right here."""
    return func(*args)


async def handle(request: str) -> str:
    """Answer one API request, both as JSON text.

    The request is ``{"method", "url", "headers": [[name, value], ...], "body"}``, with
    ``url`` like ``/api/state?x=1``. The reply is ``{"status", "headers", "body"}``.
    """
    if _app is None:
        raise RuntimeError("zimpasta.browser.start() has not been called.")
    return json.dumps(await call(_app, **json.loads(request)))


async def call(app, method: str, url: str, headers: Any = (), body: str = "") -> dict:
    """Send one request to the ASGI ``app`` in process and collect the response."""
    path, _, query = url.partition("?")
    raw = body.encode()
    # The page's own worker is the only caller, so it passes the API's local-only check
    # as a same-origin request from localhost would.
    scope_headers = [(b"host", b"localhost")]
    scope_headers += [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in headers
        if name.lower() not in ("host", "origin", "content-length")
    ]
    if raw:
        scope_headers.append((b"content-length", str(len(raw)).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": unquote(path),
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": scope_headers,
        "client": ("127.0.0.1", 0),
        "server": ("localhost", 80),
    }
    pending = [{"type": "http.request", "body": raw, "more_body": False}]

    async def receive() -> dict:
        if pending:
            return pending.pop()
        return await asyncio.get_running_loop().create_future()  # no disconnects here

    response: dict = {"status": 500, "headers": [], "body": b""}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = [
                [name.decode("latin-1"), value.decode("latin-1")]
                for name, value in message.get("headers", [])
            ]
        elif message["type"] == "http.response.body":
            response["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return {**response, "body": response["body"].decode()}
