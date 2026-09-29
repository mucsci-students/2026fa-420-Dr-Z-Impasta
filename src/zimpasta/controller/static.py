"""Serve the built React GUI next to the API.

``npm run build`` in ``frontend/`` writes the GUI into ``src/zimpasta/web/``:
``index.html`` plus hashed files under ``assets/``. This module serves those files and
answers every other non-API path with ``index.html``, so the browser's own routes
(``/editor``, ``/generator``, ``/viewer``) work on reload. If the GUI has not been built,
every page explains how to build it instead of showing a blank 404.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

BUILT_GUI = Path(__file__).resolve().parent.parent / "web"
"""Where ``npm run build`` puts the GUI."""

NOT_BUILT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Dr. ZImpasta</title>
<style>body{font:15px/1.5 system-ui,sans-serif;color:#1b1c1e;background:#f5f5f3;margin:0}
main{max-width:640px;margin:12vh auto;padding:32px;background:#fff;border:1px solid #e2e2dd;
border-radius:8px}code,pre{font:13px ui-monospace,monospace;background:#f5f5f3;border-radius:4px}
code{padding:1px 4px}pre{padding:12px 14px}</style></head>
<body><main>
<h1>The GUI hasn't been built yet</h1>
<p>The server and its API at <code>/api</code> are running, but the web interface files are
missing. From the repository root, build them once:</p>
<pre>cd frontend
npm ci
npm run build</pre>
<p>Then reload this page. To work on the GUI with live reloading, run <code>npm run dev</code>
in <code>frontend/</code> instead.</p>
</main></body></html>
"""

_NO_CACHE = {"Cache-Control": "no-cache"}


def install(app: FastAPI, static_dir: Path | None = BUILT_GUI) -> None:
    """Serve the GUI from ``static_dir``, after every API route. Call last."""
    root = static_dir.resolve() if static_dir is not None else None
    index = root / "index.html" if root is not None else None
    built = index is not None and index.is_file()

    @app.get("/{path:path}", include_in_schema=False)
    def gui(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        if not built:
            return HTMLResponse(NOT_BUILT, status_code=503, headers=_NO_CACHE)
        if path:
            candidate = (root / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
        return FileResponse(index, headers=_NO_CACHE)
