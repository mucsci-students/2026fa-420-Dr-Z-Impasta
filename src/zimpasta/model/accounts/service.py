"""Accounts and saved states: log in, and keep each state of the application in the account.

A *state* is one configuration with its schedules: for example a Biology department's
configuration and the schedules generated from it. A user can have many and switch
between them; whichever is open is saved to the account automatically.

:class:`AccountService` observes the configuration workspace and the schedule set (the
Observer pattern, :mod:`zimpasta.model.observable`). After every change to either, made
anywhere (an editor form, the AI assistant, an import, a finished run), it saves the open
state through the account store (the Repository pattern,
:class:`~zimpasta.model.accounts.records.AccountStore`). A failed save never undoes or
blocks the change: it is reported in :meth:`status` and retried with the next change, and
switching or logging out first saves explicitly, refusing to continue if that fails.

One user is logged in per running app, matching its single workspace. Logging out saves
the open state and closes it, so the next person sees nothing of it.
"""

import re
from collections.abc import Callable
from typing import Any

from zimpasta.model.accounts.passwords import check_against_nothing, hash_password, verify_password
from zimpasta.model.accounts.records import (
    AccountError,
    AccountStore,
    InvalidAccountInput,
    InvalidCredentials,
    NotLoggedIn,
    SavedState,
    StateInUse,
    StateNotFound,
    StateSummary,
    StorageUnavailable,
    User,
)
from zimpasta.model.schedules import ScheduleSet
from zimpasta.model.workspace import ConfigWorkspace, UnsavedChanges

USERNAME = re.compile(r"[a-z0-9][a-z0-9._-]{2,31}")
MIN_PASSWORD, MAX_PASSWORD = 8, 128
MAX_STATE_NAME = 60
FIRST_STATE = "My first state"
"""The name given to what was open when a new account logs in for the first time."""


class AccountService:
    """The logged-in user and their open state, kept in sync with the account store."""

    def __init__(
        self,
        workspace: ConfigWorkspace,
        schedules: ScheduleSet,
        *,
        store_factory: Callable[[], AccountStore] | None,
        unavailable_reason: str | None = None,
    ) -> None:
        """``store_factory`` connects to the account store when accounts are first used;
        ``None`` means this version of the app has no accounts, for ``unavailable_reason``."""
        self._workspace = workspace
        self._schedules = schedules
        self._factory = store_factory
        self._unavailable = unavailable_reason
        self._store: AccountStore | None = None
        self._lock = workspace.lock
        self._user: User | None = None
        self._state: StateSummary | None = None
        self._sync: dict[str, Any] = {"status": "idle", "saved_at": None, "error": None}
        workspace.subscribe(self._autosave)
        schedules.subscribe(self._autosave)

    # ---------------------------------------------------------------- reading

    @property
    def logged_in(self) -> bool:
        return self._user is not None

    def status(self) -> dict:
        """Who is logged in, which state is open, and whether it is saved. No database
        access, so it is cheap enough for the app state poll."""
        try:
            self._connect()
            available, reason = True, None
        except StorageUnavailable as error:
            available, reason = False, error.message
        with self._lock:
            return {
                "available": available,
                "reason": reason,
                "user": {"username": self._user.username} if self._user else None,
                "state": self._state.to_dict() if self._state else None,
                "sync": dict(self._sync),
            }

    def list_states(self) -> list[dict]:
        user = self._require_user()
        current = self._state.id if self._state else None
        return [
            {**state.to_dict(), "current": state.id == current}
            for state in self._connect().list_states(user.id)
        ]

    # --------------------------------------------------------------- sessions

    def sign_up(self, username: str, password: str, *, discard_changes: bool = False) -> None:
        """Create an account and log in to it.

        Raises:
            InvalidAccountInput: the username or password doesn't meet the rules.
            UsernameTaken: someone already has that username.
        """
        name = _username(username)
        _check_password(password)
        self._connect().create_user(name, hash_password(password))
        self.log_in(name, password, discard_changes=discard_changes)

    def log_in(self, username: str, password: str, *, discard_changes: bool = False) -> None:
        """Log in and open the state the user had open last time.

        A new account has no states yet, so whatever is open becomes its first state and
        nothing is lost. Otherwise the open configuration is replaced, which asks first
        when it has unsaved changes, as loading a file does.

        Raises:
            InvalidCredentials: no such user, or the wrong password (one message for both).
            UnsavedChanges: unsaved changes would be lost; call again with
                ``discard_changes=True`` to go ahead.
        """
        store = self._connect()
        user = store.find_user(username.strip().lower())
        if user is None:
            check_against_nothing(password)
            raise InvalidCredentials()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        with self._lock:
            if self._user is not None:
                self.log_out()
            states = store.list_states(user.id)
            if not states:
                saved = store.create_state(
                    user.id, FIRST_STATE, self._workspace.record(), self._schedules.record()
                )
            else:
                if self._workspace.dirty and not discard_changes:
                    raise UnsavedChanges(self._workspace.changes)
                ids = [state.id for state in states]
                target = user.last_state_id if user.last_state_id in ids else ids[0]
                found = store.get_state(user.id, target)
                if found is None:
                    raise StateNotFound()
                saved = found
                self._open(saved)
            store.set_last_state(user.id, saved.id)
            self._user, self._state = user, saved.summary()
            self._saved(saved.updated_at.isoformat(timespec="seconds"))

    def log_out(self) -> None:
        """Save the open state, then close it and log out. If the save fails, stay logged
        in, so nothing is lost; the error says why.

        Raises:
            StorageFailed: the open state couldn't be saved.
        """
        with self._lock:
            if self._user is None:
                return
            self.save_now()
            self._user = self._state = None
            self._sync = {"status": "idle", "saved_at": None, "error": None}
            self._workspace.close()
            self._schedules.restore(None)

    # ----------------------------------------------------------------- states

    def save_now(self) -> None:
        """Save the open state now.

        Raises:
            StorageFailed: it couldn't be saved; :meth:`status` says so too.
        """
        with self._lock:
            user, state = self._user, self._state
            if user is None or state is None:
                return
            try:
                saved_at = self._connect().save_state(
                    user.id, state.id, self._workspace.record(), self._schedules.record()
                )
            except AccountError as error:
                self._sync = {
                    "status": "failed",
                    "saved_at": self._sync["saved_at"],
                    "error": error.message,
                }
                raise
            self._state = StateSummary(state.id, state.name, state.created_at, saved_at)
            self._saved(saved_at.isoformat(timespec="seconds"))

    def create_state(self, name: str, *, copy_current: bool = False) -> None:
        """Save the open state, then create a new one and open it. It starts empty, or as
        a copy of the open state with ``copy_current``.

        Raises:
            StateNameTaken: the user already has a state with that name.
        """
        name = _state_name(name)
        with self._lock:
            user = self._require_user()
            self.save_now()
            configuration = self._workspace.record() if copy_current else None
            schedules = self._schedules.record() if copy_current else None
            store = self._connect()
            saved = store.create_state(user.id, name, configuration, schedules)
            self._open(saved)
            store.set_last_state(user.id, saved.id)
            self._state = saved.summary()
            self._saved(saved.updated_at.isoformat(timespec="seconds"))

    def switch_state(self, state_id: int) -> None:
        """Save the open state, then open another. If the save fails, nothing switches.

        Raises:
            StateNotFound: the user has no such state.
        """
        with self._lock:
            user = self._require_user()
            if self._state is not None and self._state.id == state_id:
                return
            store = self._connect()
            target = store.get_state(user.id, state_id)
            if target is None:
                raise StateNotFound()
            self.save_now()
            self._open(target)
            store.set_last_state(user.id, target.id)
            self._state = target.summary()
            self._saved(target.updated_at.isoformat(timespec="seconds"))

    def rename_state(self, state_id: int, name: str) -> None:
        name = _state_name(name)
        with self._lock:
            user = self._require_user()
            self._connect().rename_state(user.id, state_id, name)
            if self._state is not None and self._state.id == state_id:
                state = self._state
                self._state = StateSummary(state.id, name, state.created_at, state.updated_at)

    def delete_state(self, state_id: int) -> None:
        """Delete a state that isn't open.

        Raises:
            StateInUse: it's the open state; switch to another first.
        """
        with self._lock:
            user = self._require_user()
            if self._state is not None and self._state.id == state_id:
                raise StateInUse("This state is open. Switch to another state, then delete it.")
            self._connect().delete_state(user.id, state_id)

    # --------------------------------------------------------------- internals

    def _autosave(self) -> None:
        """Called by the workspace and schedule set after each change."""
        if self._user is None:
            return
        try:
            self.save_now()
        except AccountError:
            pass  # recorded in self._sync and shown to the user; retried on the next change

    def _open(self, saved: SavedState) -> None:
        """Put a saved state in the workspace and schedule set, or change nothing."""
        before = self._workspace.record()
        self._workspace.restore(saved.configuration or {})
        try:
            self._schedules.restore(saved.schedules)
        except Exception:
            self._workspace.restore(before)
            raise

    def _saved(self, at: str) -> None:
        self._sync = {"status": "saved", "saved_at": at, "error": None}

    def _require_user(self) -> User:
        if self._user is None:
            raise NotLoggedIn()
        return self._user

    def _connect(self) -> AccountStore:
        if self._store is not None:
            return self._store
        if self._factory is None:
            raise StorageUnavailable(self._unavailable or "Accounts aren't available here.")
        self._store = self._factory()
        return self._store


def _username(value: str) -> str:
    name = value.strip().lower()
    if not USERNAME.fullmatch(name):
        raise InvalidAccountInput(
            "A username is 3 to 32 characters: letters, digits, dots, dashes, and "
            "underscores, starting with a letter or digit."
        )
    return name


def _check_password(password: str) -> None:
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise InvalidAccountInput(
            f"A password is {MIN_PASSWORD} to {MAX_PASSWORD} characters long."
        )


def _state_name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= MAX_STATE_NAME:
        raise InvalidAccountInput(f"A state's name is 1 to {MAX_STATE_NAME} characters.")
    return name
