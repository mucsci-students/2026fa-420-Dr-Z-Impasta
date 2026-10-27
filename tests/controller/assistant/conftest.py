"""An app controller whose AI is a scripted fake and whose solver is a fast fake."""

import json
from functools import partial

import pytest

from tests.helpers import FakeAIClient
from zimpasta.controller import AppController
from zimpasta.model.generate import generation_steps


@pytest.fixture
def ai() -> FakeAIClient:
    """The fake AI. Tests add to ``ai.script`` before sending a message."""
    return FakeAIClient()


@pytest.fixture
def app(ai, fake_factory, config_data) -> AppController:
    """A controller with the two-course test fixture loaded and saved."""
    controller = AppController(
        generator=partial(generation_steps, scheduler_factory=fake_factory),
        ai_client_factory=lambda: ai,
    )
    controller.load_configuration("minimal.json", json.dumps(config_data))
    return controller
