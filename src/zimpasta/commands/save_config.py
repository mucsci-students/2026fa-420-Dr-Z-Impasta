"""Save a scheduler configuration to a JSON file.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from pathlib import Path

from zimpasta.console import Console
from zimpasta.session import Session


def save_config(console: Console, session: Session) -> None:
    """Save the current configuration to a JSON file."""
    if not session.has_config:
        console.say("No configuration is loaded.")
        return

    raw_path = console.ask("Enter configuration file path: ").strip()
    path = Path(raw_path)

    try:
        path.write_text(
            session.config.model_dump_json(indent=2),
            encoding="utf-8",
        )
    except OSError:
        console.say("Unable to save configuration.")
        return

    session.config_path = path
    console.say("Configuration saved successfully.")
