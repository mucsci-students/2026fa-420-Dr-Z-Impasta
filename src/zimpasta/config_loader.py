"""Configuration loading shared by the ``load`` command and ``run schedule --config``.

One function, so every path that reads a configuration file behaves the same way. It
wraps the library's loader and lets the library's exceptions propagate; callers turn
them into user-facing messages.
"""

import os

from scheduler import CombinedConfig, load_config_from_file


def load_config(path: str | os.PathLike[str]) -> CombinedConfig:
    """Read and validate one combined-configuration JSON file.

    Raises:
        OSError: the file cannot be opened or read.
        json.JSONDecodeError: the file is not valid JSON.
        pydantic.ValidationError: the document is not a valid ``CombinedConfig``.
    """
    return load_config_from_file(CombinedConfig, path)
