"""Wording and choices that several shell commands share, so they stay identical."""

KINDS: tuple[str, ...] = ("course", "room", "lab", "faculty")
"""The item categories ``add`` and ``delete`` work on, in the order their menus list them."""

NO_CONFIG_TO_EDIT = "No configuration loaded. Load one first."
"""What ``add``, ``delete``, and ``modify`` say when nothing is loaded."""

NO_CONFIG_LOADED = "No configuration is loaded."
"""What ``print`` and ``save`` say when nothing is loaded."""

PATH_PROMPT = "Enter configuration file path: "
"""How ``load`` and ``save`` ask for a configuration file's path."""
