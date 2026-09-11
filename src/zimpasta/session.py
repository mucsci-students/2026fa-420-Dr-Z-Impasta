"""Shared in-memory state for one interactive session.

One ``Session`` is created when the shell starts and handed to every command. Features
communicate through it instead of through globals or loose return values:

* the config-loading feature fills ``config`` and ``config_path``;
* add, modify, and delete edit ``config`` (see ``CombinedConfig.edit_mode()`` in the
  library for atomic, validated edits);
* run-the-scheduler reads ``config`` and stores its results here;
* display reads whatever is here.

Add a field for state your feature keeps between commands. Keep the library's
``CombinedConfig`` as the single source of truth; do not mirror its contents.
"""

from dataclasses import dataclass
from pathlib import Path

from scheduler import CombinedConfig


@dataclass
class Session:
    config: CombinedConfig | None = None
    """The validated in-memory configuration, or ``None`` before one is loaded."""

    config_path: Path | None = None
    """Where ``config`` was loaded from, when it came from a file."""

    @property
    def has_config(self) -> bool:
        return self.config is not None
