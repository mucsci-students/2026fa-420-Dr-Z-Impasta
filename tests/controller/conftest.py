from functools import partial

import pytest
from fastapi.testclient import TestClient

from tests.helpers import FakeSchedulerFactory
from zimpasta.controller import AppController, create_app
from zimpasta.model.generate import generate_schedules

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def fake_factory(real_schedules) -> FakeSchedulerFactory:
    return FakeSchedulerFactory(real_schedules)


@pytest.fixture
def controller(fake_factory) -> AppController:
    """A controller whose scheduler is a fast fake that yields the fixture's real schedules."""
    return AppController(generator=partial(generate_schedules, scheduler_factory=fake_factory))


@pytest.fixture
def client(controller) -> TestClient:
    return TestClient(create_app(controller), base_url=BASE_URL)
