"""Configuration-loading seam.

STUB for the "Load / specify / parse config file" feature. The run-scheduler command
depends on this one function only. Replace the body, keep the signature and the
documented exceptions, and nothing in the run-scheduler feature needs to change.
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
