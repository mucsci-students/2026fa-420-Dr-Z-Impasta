"""The Controller: user actions in, Model calls out.

* :mod:`~zimpasta.controller.app_controller` has one method per GUI action and does the
  coordination (for example, moving generated schedules into the viewer). It has no HTTP
  in it, so it is tested directly with pytest.
* :mod:`~zimpasta.controller.routes` is the ``/api`` HTTP surface the React views call;
  each route calls one controller method.
* :mod:`~zimpasta.controller.errors` turns Model failures into one JSON error shape.
* :mod:`~zimpasta.controller.security` keeps the local server local.
* :func:`create_app` wires them into a FastAPI application.
"""

from zimpasta.controller.api import create_app
from zimpasta.controller.app_controller import AppController

__all__ = ["AppController", "create_app"]
