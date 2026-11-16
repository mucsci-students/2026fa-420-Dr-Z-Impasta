"""A live test against the real account database (Neon): one throwaway account.

Deselected by default like every live test; run it with ``uv run pytest -m live``. It
reads DATABASE_URL from the environment or the .env file and is skipped without it. It
creates a uniquely named user, saves and reopens states through a second connection to
prove they persisted, and deletes the user (and so its states) at the end.
"""

import json
import os
import uuid

import pytest
from dotenv import dotenv_values, find_dotenv

from zimpasta.model.accounts import AccountService
from zimpasta.model.accounts.sql_store import SqlAccountStore
from zimpasta.model.schedules import ScheduleSet
from zimpasta.model.workspace import ConfigWorkspace

URL = os.environ.get("DATABASE_URL") or dotenv_values(find_dotenv(usecwd=True)).get("DATABASE_URL")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not URL, reason="DATABASE_URL is not set, so the live Neon test is skipped."
    ),
]

PASSWORD = "live test password"


def test_states_persist_in_the_real_database(config_data):
    assert URL is not None
    store = SqlAccountStore.from_url(URL)
    username = f"zimpasta-live-{uuid.uuid4().hex[:10]}"
    workspace, schedules = ConfigWorkspace(), ScheduleSet()
    workspace.load_text(json.dumps(config_data), filename="biology.json")
    service = AccountService(workspace, schedules, store_factory=lambda: store)
    try:
        service.sign_up(username, PASSWORD)
        workspace.add("rooms", {"name": "Live Room", "capacity": 12})
        service.create_state("Chemistry")
        service.log_out()

        fresh = SqlAccountStore.from_url(URL)  # a new connection pool, as after a restart
        reopened = AccountService(ConfigWorkspace(), ScheduleSet(), store_factory=lambda: fresh)
        reopened.log_in(username, PASSWORD)
        names = {state["name"] for state in reopened.list_states()}
        assert names == {"My first state", "Chemistry"}
        assert reopened.status()["state"]["name"] == "Chemistry"
        first = next(s["id"] for s in reopened.list_states() if s["name"] == "My first state")
        reopened.switch_state(first)
        assert "Live Room" in [room["name"] for room in reopened._workspace.items("rooms")]
    finally:
        user = store.find_user(username)
        if user is not None:
            store.delete_user(user.id)
