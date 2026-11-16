"""Wording, choices, and the configuration loader that several shell commands share."""

import json
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.model.config_loader import load_config as read_config
from zimpasta.session import Session

KINDS: tuple[str, ...] = ("course", "room", "lab", "faculty")
"""The item categories ``add`` and ``delete`` work on, in the order their menus list them."""

NO_CONFIG_TO_EDIT = "No configuration loaded. Load one first."
"""What ``add``, ``delete``, and ``modify`` say when nothing is loaded."""

NO_CONFIG_LOADED = "No configuration is loaded."
"""What ``print`` and ``save`` say when nothing is loaded."""

PATH_PROMPT = "Enter configuration file path: "
"""How ``load`` and ``save`` ask for a configuration file's path."""


LoadError = OSError | json.JSONDecodeError | ValidationError
"""Why a configuration file couldn't be loaded. Each command words it its own way."""


def read_into_session(
    session: Session, path: Path, loader: Callable[[Path], CombinedConfig] = read_config
) -> LoadError | None:
    """Load ``path`` into the session, or return why it couldn't be loaded.

    Shared by ``load`` and ``run schedule --config``. The session is only updated after a
    successful load, so a bad path or an invalid file leaves the previous configuration.
    """
    try:
        config = loader(path)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        return error
    session.config = config
    session.config_path = path.resolve()
    return None
