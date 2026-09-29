"""Keep the local server reachable only by this computer's own browser tab.

The server listens on 127.0.0.1, but any web page open in the same browser could still
try to send it requests. Three checks stop that:

* **Host** must be ``localhost``, ``127.0.0.1``, or ``[::1]``. This defeats DNS
  rebinding, where a hostile domain is pointed at 127.0.0.1.
* **Origin**, when a browser sends one on a state-changing request, must match the host
  the request was sent to, so another site can't submit to the API.
* **Content-Type** must be JSON when a ``POST``, ``PUT``, or ``PATCH`` to ``/api`` has a
  body. A cross-site JSON request needs a CORS preflight, which this server never grants,
  and an HTML form can't send JSON. Body-less POSTs (such as cancel) rely on the Origin
  check, since browsers always send Origin on POST.

No CORS headers are sent at all: the GUI is served from the same origin as the API.
"""

from collections.abc import Iterable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from zimpasta.controller.errors import error_body

DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_BODY_METHODS = {"POST", "PUT", "PATCH"}


def host_name(host_header: str) -> str:
    """``127.0.0.1:8000`` -> ``127.0.0.1``; ``[::1]:8000`` -> ``[::1]``."""
    host_header = host_header.strip().lower()
    if host_header.startswith("["):
        return host_header[: host_header.find("]") + 1]
    return host_header.split(":", 1)[0]


def install(app: FastAPI, allowed_hosts: Iterable[str] = DEFAULT_ALLOWED_HOSTS) -> None:
    allowed = {host.lower() for host in allowed_hosts}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.headers.get("host", "")
        if host_name(host) not in allowed:
            return _refuse(400, "bad_host", "This server only answers requests for localhost.")

        method = request.method.upper()
        if method not in _SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and (
                origin == "null" or urlsplit(origin).netloc.lower() != host.lower()
            ):
                return _refuse(403, "cross_origin", "Requests from other sites are not allowed.")
            if (
                method in _BODY_METHODS
                and request.url.path.startswith("/api/")
                and _has_body(request)
                and not request.headers.get("content-type", "")
                .lower()
                .startswith("application/json")
            ):
                return _refuse(415, "json_required", "Send the request body as JSON.")
        return await call_next(request)


def _has_body(request: Request) -> bool:
    length = request.headers.get("content-length")
    return "transfer-encoding" in request.headers or (length is not None and length != "0")


def _refuse(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(error_body(code, message), status_code=status)
