"""The SQL account store: users, states, ownership, and database failures."""

import pytest
from sqlalchemy.engine import make_url

from zimpasta.model.accounts import (
    StateNameTaken,
    StateNotFound,
    StorageFailed,
    StorageUnavailable,
    UsernameTaken,
    store_from_environment,
)
from zimpasta.model.accounts.sql_store import SqlAccountStore, engine_for

CONFIG = {"document": {"limit": 3}, "name": "biology.json"}
SCHEDULES = {"schedules": [], "source": None}


def test_users_are_created_found_and_unique(store):
    created = store.create_user("ada", "scrypt$hash")

    found = store.find_user("ada")
    assert found is not None
    assert (found.id, found.username, found.password_hash) == (created.id, "ada", "scrypt$hash")
    assert found.created_at.tzinfo is not None
    assert found.last_state_id is None
    assert store.find_user("grace") is None
    with pytest.raises(UsernameTaken):
        store.create_user("ada", "other")


def test_states_are_created_listed_newest_first_and_saved(store):
    user = store.create_user("ada", "h")
    biology = store.create_state(user.id, "Biology", CONFIG, SCHEDULES)
    chemistry = store.create_state(user.id, "Chemistry", None, None)

    assert [state.name for state in store.list_states(user.id)] == ["Chemistry", "Biology"]

    saved_at = store.save_state(user.id, biology.id, {"document": {"limit": 9}}, None)

    assert [state.name for state in store.list_states(user.id)] == ["Biology", "Chemistry"]
    reopened = store.get_state(user.id, biology.id)
    assert reopened is not None
    assert reopened.configuration == {"document": {"limit": 9}}
    assert reopened.schedules is None
    assert reopened.updated_at == saved_at > chemistry.updated_at


def test_one_user_can_never_reach_another_users_states(store):
    ada, grace = store.create_user("ada", "h"), store.create_user("grace", "h")
    private = store.create_state(ada.id, "Biology", CONFIG, None)

    assert store.get_state(grace.id, private.id) is None
    assert store.list_states(grace.id) == []
    with pytest.raises(StateNotFound):
        store.save_state(grace.id, private.id, None, None)
    with pytest.raises(StateNotFound):
        store.rename_state(grace.id, private.id, "Mine now")
    with pytest.raises(StateNotFound):
        store.delete_state(grace.id, private.id)
    assert store.get_state(ada.id, private.id) is not None


def test_state_names_are_unique_per_user_only(store):
    ada, grace = store.create_user("ada", "h"), store.create_user("grace", "h")
    store.create_state(ada.id, "Biology", None, None)
    chemistry = store.create_state(ada.id, "Chemistry", None, None)

    store.create_state(grace.id, "Biology", None, None)
    with pytest.raises(StateNameTaken):
        store.create_state(ada.id, "Biology", None, None)
    with pytest.raises(StateNameTaken):
        store.rename_state(ada.id, chemistry.id, "Biology")

    store.rename_state(ada.id, chemistry.id, "Physics")
    assert {state.name for state in store.list_states(ada.id)} == {"Biology", "Physics"}


def test_deleting_a_state_forgets_it_as_the_last_one_opened(store):
    user = store.create_user("ada", "h")
    state = store.create_state(user.id, "Biology", None, None)
    store.set_last_state(user.id, state.id)

    store.delete_state(user.id, state.id)

    assert store.get_state(user.id, state.id) is None
    found = store.find_user("ada")
    assert found is not None and found.last_state_id is None


def test_deleting_a_user_deletes_their_states(store):
    user = store.create_user("ada", "h")
    state = store.create_state(user.id, "Biology", None, None)

    store.delete_user(user.id)

    assert store.find_user("ada") is None
    assert store.get_state(user.id, state.id) is None


def test_an_unreachable_database_is_a_storage_failure(tmp_path):
    store = SqlAccountStore(engine_for(f"sqlite:///{tmp_path}/missing/folder/db.sqlite"))

    with pytest.raises(StorageFailed) as caught:
        store.find_user("ada")

    assert "Couldn't reach the account database" in caught.value.message
    assert caught.value.code == "account_storage_failed"


def test_neon_connection_strings_use_psycopg():
    engine = engine_for("postgresql://user:secret@ep-example.neon.tech/app?sslmode=require")

    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.query["sslmode"] == "require"
    assert engine_for("postgres://u:p@host/db").url.drivername == "postgresql+psycopg"
    assert make_url(str(engine_for("sqlite://").url)).drivername == "sqlite"


def test_the_store_comes_from_database_url():
    with pytest.raises(StorageUnavailable, match="DATABASE_URL"):
        store_from_environment({})
    with pytest.raises(StorageUnavailable):
        store_from_environment({"DATABASE_URL": "   "})

    store = store_from_environment({"DATABASE_URL": "sqlite://"})
    assert isinstance(store, SqlAccountStore)
    assert store.find_user("nobody") is None
