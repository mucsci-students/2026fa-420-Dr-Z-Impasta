"""Load a scheduler configuration from a JSON file.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from pathlib import Path

from pydantic import ValidationError
from scheduler import CombinedConfig

from zimpasta.console import Console
from zimpasta.session import Session


def load_config(console: Console, session: Session) -> None:
    """Load and validate a scheduler configuration from a JSON file."""
    while True:
        raw_path = console.ask("Enter configuration file path: ").strip()
        path = Path(raw_path)

        try:
            config_text = path.read_text(encoding="utf-8")
            new_config = CombinedConfig.model_validate_json(config_text)
        except FileNotFoundError:
            console.say("File not found.")
            continue
        except OSError:
            console.say("Unable to read file.")
            continue
        except ValidationError:
            console.say("Invalid configuration file.")
            continue

        # Assign only after validation so a failed load cannot replace a valid configuration.
        session.config = new_config
        session.config_path = path
        console.say("Configuration loaded successfully.")
        return
