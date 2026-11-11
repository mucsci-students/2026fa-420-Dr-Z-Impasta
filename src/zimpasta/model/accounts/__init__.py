"""User accounts and saved application states. See docs/accounts.md.

``service.py`` logs users in and keeps the open state saved, ``records.py`` defines the
store's interface and errors, ``sql_store.py`` implements the store on PostgreSQL (Neon)
or SQLite, and ``passwords.py`` hashes passwords. SQLAlchemy is imported only when a store
is created, so the browser version, which has no database, can import this package.
"""

import os
from collections.abc import Mapping

from zimpasta.model.accounts.records import (
    AccountError,
    AccountStore,
    InvalidAccountInput,
    InvalidCredentials,
    NotLoggedIn,
    StateInUse,
    StateNameTaken,
    StateNotFound,
    StorageFailed,
    StorageUnavailable,
    UsernameTaken,
)
from zimpasta.model.accounts.service import AccountService

DATABASE_VARIABLE = "DATABASE_URL"

__all__ = [
    "DATABASE_VARIABLE",
    "AccountError",
    "AccountService",
    "AccountStore",
    "InvalidAccountInput",
    "InvalidCredentials",
    "NotLoggedIn",
    "StateInUse",
    "StateNameTaken",
    "StateNotFound",
    "StorageFailed",
    "StorageUnavailable",
    "UsernameTaken",
    "store_from_environment",
]


def store_from_environment(environ: Mapping[str, str] | None = None) -> AccountStore:
    """The account store named by ``DATABASE_URL`` (Neon's connection string).

    Raises:
        StorageUnavailable: ``DATABASE_URL`` isn't set.
    """
    environ = os.environ if environ is None else environ
    url = environ.get(DATABASE_VARIABLE, "").strip()
    if not url:
        raise StorageUnavailable(
            f"Accounts need a database. Put the Neon connection string in {DATABASE_VARIABLE} "
            "in the .env file and restart the app (see docs/accounts.md)."
        )
    from zimpasta.model.accounts.sql_store import SqlAccountStore

    return SqlAccountStore.from_url(url)
