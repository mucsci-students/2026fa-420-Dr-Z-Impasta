"""What the account store keeps, the errors accounts can raise, and the store's interface.

:class:`AccountStore` is the Repository pattern's interface: the rest of the application
asks it for users and saved states by meaning ("the states of user 7", "save this state")
and never sees SQL. :class:`~zimpasta.model.accounts.sql_store.SqlAccountStore` implements
it on PostgreSQL (Neon) for the app and on SQLite for the tests.

This module imports no database library, so the parts of the app that only need these
types (including the browser version, which has no database) can import it freely.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    created_at: datetime
    last_state_id: int | None = None
    """The state that was open when the user last used the app, reopened at login."""


@dataclass(frozen=True)
class StateSummary:
    """One saved state, without its contents."""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "updated_at": self.updated_at.isoformat(timespec="seconds"),
        }


@dataclass(frozen=True)
class SavedState:
    """One saved state with its contents, as recorded by the workspace and schedule set."""

    id: int
    user_id: int
    name: str
    configuration: dict[str, Any] | None
    schedules: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    def summary(self) -> StateSummary:
        return StateSummary(self.id, self.name, self.created_at, self.updated_at)


class AccountError(Exception):
    """Base class for account failures. ``message`` is written for the user."""

    code = "account_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StorageUnavailable(AccountError):
    """This copy of the app has no account database (no DATABASE_URL, or the browser
    version)."""

    code = "accounts_unavailable"


class StorageFailed(AccountError):
    """The account database couldn't be reached or refused a request."""

    code = "account_storage_failed"


class InvalidAccountInput(AccountError):
    code = "invalid_account_input"


class UsernameTaken(AccountError):
    code = "username_taken"


class InvalidCredentials(AccountError):
    code = "invalid_credentials"

    def __init__(self) -> None:
        super().__init__("That username and password don't match an account.")


class NotLoggedIn(AccountError):
    code = "not_logged_in"

    def __init__(self) -> None:
        super().__init__("Log in to use saved states.")


class StateNotFound(AccountError):
    code = "state_not_found"

    def __init__(self) -> None:
        super().__init__("That saved state doesn't exist.")


class StateNameTaken(AccountError):
    code = "state_name_taken"


class StateInUse(AccountError):
    code = "state_in_use"


class AccountStore(Protocol):
    """Where users and their saved states are kept (the Repository pattern).

    Every method that reads or changes a state takes the owner's user id, so one user can
    never reach another's states. Failures to reach the database raise
    :class:`StorageFailed`.
    """

    def create_user(self, username: str, password_hash: str) -> User:
        """Raises :class:`UsernameTaken` if the username is in use."""
        ...

    def find_user(self, username: str) -> User | None: ...

    def delete_user(self, user_id: int) -> None:
        """Delete the user and all of their states."""
        ...

    def set_last_state(self, user_id: int, state_id: int | None) -> None: ...

    def list_states(self, user_id: int) -> list[StateSummary]:
        """The user's states, most recently saved first."""
        ...

    def create_state(
        self,
        user_id: int,
        name: str,
        configuration: dict[str, Any] | None,
        schedules: dict[str, Any] | None,
    ) -> SavedState:
        """Raises :class:`StateNameTaken` if the user already has a state with this name."""
        ...

    def get_state(self, user_id: int, state_id: int) -> SavedState | None: ...

    def save_state(
        self,
        user_id: int,
        state_id: int,
        configuration: dict[str, Any] | None,
        schedules: dict[str, Any] | None,
    ) -> datetime:
        """Replace the state's contents. Returns when it was saved.

        Raises :class:`StateNotFound` if the user has no such state.
        """
        ...

    def rename_state(self, user_id: int, state_id: int, name: str) -> None:
        """Raises :class:`StateNotFound` or :class:`StateNameTaken`."""
        ...

    def delete_state(self, user_id: int, state_id: int) -> None:
        """Raises :class:`StateNotFound`."""
        ...
