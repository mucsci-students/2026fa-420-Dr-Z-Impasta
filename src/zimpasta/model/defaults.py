"""Starting values for a new configuration.

The time grid and class patterns come from the scheduler library's own department
example (``examples/sample_config.json``): MWF and TR lecture patterns plus the lab
patterns that go with them, 9 of 16 enabled. A new configuration starts with these so
courses can be added straight away; they remain fully editable.
"""

import copy
import json
from functools import cache
from importlib import resources

DEFAULT_LIMIT = 10
"""The library's own default generation limit."""


@cache
def _default_time_slots() -> dict:
    text = (
        resources.files("zimpasta.model")
        .joinpath("data/default_time_slots.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


def default_time_slot_config() -> dict:
    """A fresh copy of the default ``time_slot_config`` document."""
    return copy.deepcopy(_default_time_slots())


def empty_configuration() -> dict:
    """A new configuration document: default time slots, no rooms, labs, courses, or faculty."""
    return {
        "config": {"rooms": [], "labs": [], "courses": [], "faculty": []},
        "time_slot_config": default_time_slot_config(),
        "limit": DEFAULT_LIMIT,
        "optimizer_flags": [],
    }
