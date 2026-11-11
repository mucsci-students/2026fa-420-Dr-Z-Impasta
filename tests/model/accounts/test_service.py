"""Accounts and saved states: sign up, log in, autosave, switch, and failures."""

import json

import pytest

from tests.model.accounts.conftest import PASSWORD
from zimpasta.model.accounts import (
    AccountService,
    InvalidAccountInput,
    InvalidCredentials,
    NotLoggedIn,
    StateInUse,
    StateNameTaken,
    StateNotFound,
    StorageFailed,
    UsernameTaken,
)
from zimpasta.model.workspace import EditRejected, UnsavedChanges

ROOM = {"name": "Room 201", "capacity": 30}
SCHEDULE_FILE = json.dumps(
    [
        [
            {
                "course": "CS 101.01",
                "faculty": "Dr. Smith",
                "room": "Room 101",
                "times": [{"day": 1, "start": 540, "duration": 50, "delivery": "in_person"}],
                "reserve_room_during_lab": False,
            }
        ]
    ]
)


def rooms(workspace) -> list[str]:
    return [room["name"] for room in workspace.items("rooms")]


def saved_configuration(store, service) -> dict:
    status = service.status()
    user = store.find_user(status["user"]["username"])
    state = store.get_state(user.id, status["state"]["id"])
    return state.configuration


def state_named(service, name: str) -> dict:
    return next(state for state in service.list_states() if state["name"] == name)


# ------------------------------------------------------------------ availability


def test_without_a_store_accounts_say_why(workspace, schedules):
    service = AccountService(
        workspace, schedules, store_factory=None, unavailable_reason="Not in the browser."
    )

    status = service.status()
    assert status["available"] is False and status["reason"] == "Not in the browser."
    assert status["user"] is None
    with pytest.raises(NotLoggedIn):
        service.list_states()


def test_status_before_anyone_logs_in(service):
    assert service.status() == {
        "available": True,
        "reason": None,
        "user": None,
        "state": None,
        "sync": {"status": "idle", "saved_at": None, "error": None},
    }


# ------------------------------------------------------------ signing up and in


@pytest.mark.parametrize("username", ["ab", "-ada", "ada lovelace", "a" * 33, "ada!"])
def test_usernames_follow_the_rules(service, username):
    with pytest.raises(InvalidAccountInput, match="3 to 32 characters"):
        service.sign_up(username, PASSWORD)


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_passwords_follow_the_rules(service, password):
    with pytest.raises(InvalidAccountInput, match="8 to 128 characters"):
        service.sign_up("ada", password)


def test_signing_up_logs_in_and_keeps_what_was_open_as_the_first_state(service, loaded, store):
    service.sign_up("  Ada  ", PASSWORD)

    status = service.status()
    assert status["user"] == {"username": "ada"}
    assert status["state"]["name"] == "My first state"
    assert status["sync"]["status"] == "saved"
    assert saved_configuration(store, service)["name"] == "biology.json"
    assert rooms(loaded) == ["Room 101"]
    with pytest.raises(UsernameTaken):
        AccountService(loaded, service._schedules, store_factory=lambda: store).sign_up(
            "ADA", PASSWORD
        )


def test_wrong_passwords_and_unknown_users_get_the_same_answer(service):
    service.sign_up("ada", PASSWORD)
    service.log_out()

    with pytest.raises(InvalidCredentials) as wrong:
        service.log_in("ada", "not the password")
    with pytest.raises(InvalidCredentials) as unknown:
        service.log_in("nobody", PASSWORD)

    assert wrong.value.message == unknown.value.message
    assert service.status()["user"] is None


# ------------------------------------------------------------------- autosave


def test_every_edit_is_saved_to_the_open_state(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    saves = store.saves

    loaded.add("rooms", ROOM)

    assert store.saves == saves + 1
    document = saved_configuration(store, service)["document"]
    assert [room["name"] for room in document["config"]["rooms"]] == ["Room 101", "Room 201"]


def test_imported_and_cleared_schedules_are_saved(service, loaded, schedules, store):
    service.sign_up("ada", PASSWORD)

    schedules.import_text(SCHEDULE_FILE, filename="fall.json")
    user = store.find_user("ada")
    state = store.get_state(user.id, service.status()["state"]["id"])
    assert state.schedules["name"] == "fall.json"
    assert len(state.schedules["schedules"]) == 1

    schedules.clear()
    state = store.get_state(user.id, state.id)
    assert state.schedules["schedules"] == []


def test_a_combined_edit_is_saved_once_and_a_failed_one_not_at_all(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    saves = store.saves

    with loaded.transaction():
        loaded.add("rooms", ROOM)
        loaded.add("rooms", {"name": "Room 301", "capacity": 20})
    assert store.saves == saves + 1

    with pytest.raises(EditRejected):
        with loaded.transaction():
            loaded.add("rooms", {"name": "Room 401", "capacity": 10})
            loaded.update_settings({"limit": -1})
    assert store.saves == saves + 1
    assert "Room 401" not in rooms(loaded)


def test_nothing_is_saved_while_logged_out(service, loaded, store):
    loaded.add("rooms", ROOM)

    assert store.saves == 0


def test_a_failed_save_never_undoes_the_edit_and_is_reported(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    store.failing = True

    loaded.add("rooms", ROOM)

    assert "Room 201" in rooms(loaded)
    sync = service.status()["sync"]
    assert sync["status"] == "failed" and "Couldn't reach" in sync["error"]

    store.failing = False
    loaded.update_settings({"limit": 4})
    assert service.status()["sync"]["status"] == "saved"
    assert saved_configuration(store, service)["document"]["limit"] == 4


# --------------------------------------------------------------------- states


def test_a_new_state_starts_empty_and_switching_back_restores_everything(
    service, loaded, schedules
):
    service.sign_up("ada", PASSWORD)
    loaded.add("rooms", ROOM)
    schedules.import_text(SCHEDULE_FILE, filename="fall.json")

    service.create_state("Chemistry")

    assert service.status()["state"]["name"] == "Chemistry"
    assert loaded.status.value == "none"
    assert schedules.count == 0

    service.switch_state(state_named(service, "My first state")["id"])

    assert rooms(loaded) == ["Room 101", "Room 201"]
    assert loaded.name == "biology.json"
    assert loaded.dirty and [change.summary for change in loaded.changes] == ["Added room Room 201"]
    assert schedules.count == 1 and schedules.summary()["name"] == "fall.json"


def test_a_state_can_start_as_a_copy_of_the_open_one(service, loaded):
    service.sign_up("ada", PASSWORD)

    service.create_state("Biology, spring", copy_current=True)
    loaded.add("rooms", ROOM)
    service.switch_state(state_named(service, "My first state")["id"])

    assert rooms(loaded) == ["Room 101"]
    service.switch_state(state_named(service, "Biology, spring")["id"])
    assert rooms(loaded) == ["Room 101", "Room 201"]


def test_states_persist_across_logging_out_and_in(service, loaded, schedules):
    service.sign_up("ada", PASSWORD)
    service.create_state("Chemistry", copy_current=True)
    loaded.update_settings({"limit": 7})

    service.log_out()

    assert service.status()["user"] is None
    assert loaded.status.value == "none" and schedules.count == 0

    service.log_in("ada", PASSWORD)

    assert service.status()["state"]["name"] == "Chemistry"
    assert loaded.document()["limit"] == 7
    assert [state["name"] for state in service.list_states()] == ["Chemistry", "My first state"]
    assert [state["current"] for state in service.list_states()] == [True, False]


def test_logging_in_over_unsaved_work_asks_first(service, loaded, config_data):
    service.sign_up("ada", PASSWORD)
    service.log_out()
    loaded.load_text(json.dumps(config_data), filename="scratch.json")
    loaded.add("rooms", ROOM)

    with pytest.raises(UnsavedChanges):
        service.log_in("ada", PASSWORD)
    assert service.status()["user"] is None and "Room 201" in rooms(loaded)

    service.log_in("ada", PASSWORD, discard_changes=True)
    assert loaded.name == "biology.json"


def test_logging_in_as_someone_else_never_hands_them_the_open_work(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    loaded.add("rooms", ROOM)
    other = AccountService(
        loaded.__class__(), service._schedules.__class__(), store_factory=lambda: store
    )
    other.sign_up("grace", PASSWORD)

    service.log_in("grace", PASSWORD)

    assert loaded.status.value == "none"
    service.log_in("ada", PASSWORD)
    assert "Room 201" in rooms(loaded)


def test_renaming_and_deleting_states(service, loaded):
    service.sign_up("ada", PASSWORD)
    service.create_state("Chemistry")
    first = state_named(service, "My first state")["id"]

    service.rename_state(first, "Biology")
    service.rename_state(service.status()["state"]["id"], "  Organic   chemistry ")

    assert service.status()["state"]["name"] == "Organic chemistry"
    with pytest.raises(StateNameTaken):
        service.rename_state(first, "Organic chemistry")
    with pytest.raises(StateInUse):
        service.delete_state(service.status()["state"]["id"])
    with pytest.raises(InvalidAccountInput):
        service.create_state("   ")

    service.delete_state(first)
    assert [state["name"] for state in service.list_states()] == ["Organic chemistry"]


def test_switching_needs_a_state_of_your_own(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    grace = store.create_user("grace", "h")
    private = store.create_state(grace.id, "Secret", None, None)

    with pytest.raises(StateNotFound):
        service.switch_state(private.id)
    assert service.status()["state"]["name"] == "My first state"


def test_switching_stays_put_when_the_open_state_cannot_be_saved(service, loaded, store):
    service.sign_up("ada", PASSWORD)
    service.create_state("Chemistry")
    loaded.close()
    target = state_named(service, "My first state")["id"]
    store.failing = True

    with pytest.raises(StorageFailed):
        service.switch_state(target)
    with pytest.raises(StorageFailed):
        service.log_out()

    assert service.status()["state"]["name"] == "Chemistry"
    assert service.status()["user"] == {"username": "ada"}


def test_reopening_never_reuses_a_revision(service, loaded):
    service.sign_up("ada", PASSWORD)
    before = loaded.revision
    service.create_state("Chemistry")
    service.switch_state(state_named(service, "My first state")["id"])

    assert loaded.revision > before
