"""An account store on in-memory SQLite, and a service observing a fresh workspace."""

import itertools
import json
from datetime import UTC, datetime, timedelta

import pytest

from zimpasta.model.accounts import AccountService, StorageFailed
from zimpasta.model.accounts.sql_store import SqlAccountStore, engine_for
from zimpasta.model.schedules import ScheduleSet
from zimpasta.model.workspace import ConfigWorkspace

PASSWORD = "correct horse battery"


def ticking_clock():
    """A clock that moves one second per reading, so save times are distinct and ordered."""
    start = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
    ticks = itertools.count()
    return lambda: start + timedelta(seconds=next(ticks))


class FlakyStore(SqlAccountStore):
    """A store whose saves can be made to fail, like a lost connection to Neon."""

    failing = False
    saves = 0

    def save_state(self, user_id, state_id, configuration, schedules):
        if self.failing:
            raise StorageFailed("Couldn't reach the account database.")
        self.saves += 1
        return super().save_state(user_id, state_id, configuration, schedules)


@pytest.fixture
def store() -> FlakyStore:
    return FlakyStore(engine_for("sqlite://"), clock=ticking_clock())


@pytest.fixture
def workspace() -> ConfigWorkspace:
    return ConfigWorkspace()


@pytest.fixture
def schedules() -> ScheduleSet:
    return ScheduleSet()


@pytest.fixture
def service(store, workspace, schedules) -> AccountService:
    return AccountService(workspace, schedules, store_factory=lambda: store)


@pytest.fixture
def loaded(workspace, config_data) -> ConfigWorkspace:
    """The workspace with the two-course fixture open and saved."""
    workspace.load_text(json.dumps(config_data), filename="biology.json")
    return workspace
