"""The account store on a SQL database: PostgreSQL (Neon) for the app, SQLite for tests.

Two tables, created on first use if they don't exist:

``users``
    ``id``, ``username`` (unique, lowercase), ``password_hash``, ``created_at``, and
    ``last_state_id``.
``states``
    ``id``, ``user_id``, ``name`` (unique per user), ``configuration`` and ``schedules``
    (JSON, as recorded by the workspace and the schedule set), ``created_at``,
    ``updated_at``. Deleting a user deletes their states.

Database errors never escape: they become :class:`StorageFailed` with a message for the
user, and the details (never the connection string) go to the log.
"""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    insert,
    select,
    update,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import StaticPool

from zimpasta.model.accounts.records import (
    SavedState,
    StateNameTaken,
    StateNotFound,
    StateSummary,
    StorageFailed,
    User,
    UsernameTaken,
)

logger = logging.getLogger("zimpasta.accounts")

T = TypeVar("T")

UNREACHABLE = (
    "Couldn't reach the account database. Check your internet connection and the "
    "DATABASE_URL setting, then try again."
)

metadata = MetaData()

users = Table(
    "zimpasta_users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_state_id", Integer, nullable=True),
)

states = Table(
    "zimpasta_states",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "user_id",
        Integer,
        ForeignKey("zimpasta_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("name", String(120), nullable=False),
    Column("configuration", JSON, nullable=True),
    Column("schedules", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_id", "name", name="zimpasta_states_user_name"),
)


def engine_for(url: str) -> Engine:
    """An engine for a database URL, such as Neon's ``postgresql://...`` connection string
    or ``sqlite://`` (in memory, for tests)."""
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    if parsed.drivername.startswith("postgresql"):
        return create_engine(
            parsed,
            pool_pre_ping=True,  # Neon closes idle connections
            pool_recycle=300,
            # Neon's pooled endpoint runs PgBouncer, which doesn't keep prepared statements.
            connect_args={"connect_timeout": 10, "prepare_threshold": None},
        )
    if parsed.drivername.startswith("sqlite"):
        engine = create_engine(
            parsed, poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        event.listen(engine, "connect", _sqlite_foreign_keys)
        return engine
    return create_engine(parsed, pool_pre_ping=True)


def _sqlite_foreign_keys(connection: Any, _record: Any) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class SqlAccountStore:
    """:class:`~zimpasta.model.accounts.records.AccountStore` on SQLAlchemy Core."""

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))
        self._ready = False
        self._ready_lock = threading.Lock()

    @classmethod
    def from_url(cls, url: str) -> "SqlAccountStore":
        return cls(engine_for(url))

    # ------------------------------------------------------------------ users

    def create_user(self, username: str, password_hash: str) -> User:
        def run(connection) -> User:
            created = self._clock()
            result = connection.execute(
                insert(users).values(
                    username=username, password_hash=password_hash, created_at=created
                )
            )
            return User(int(result.inserted_primary_key[0]), username, password_hash, created)

        try:
            return self._write(run)
        except IntegrityError:
            raise UsernameTaken(f"The username {username!r} is taken.") from None

    def find_user(self, username: str) -> User | None:
        def run(connection) -> User | None:
            row = connection.execute(select(users).where(users.c.username == username)).first()
            if row is None:
                return None
            return User(
                row.id, row.username, row.password_hash, _utc(row.created_at), row.last_state_id
            )

        return self._read(run)

    def delete_user(self, user_id: int) -> None:
        def run(connection) -> None:
            connection.execute(delete(states).where(states.c.user_id == user_id))
            connection.execute(delete(users).where(users.c.id == user_id))

        self._write(run)

    def set_last_state(self, user_id: int, state_id: int | None) -> None:
        self._write(
            lambda connection: connection.execute(
                update(users).where(users.c.id == user_id).values(last_state_id=state_id)
            )
        )

    # ----------------------------------------------------------------- states

    def list_states(self, user_id: int) -> list[StateSummary]:
        def run(connection) -> list[StateSummary]:
            rows = connection.execute(
                select(states.c.id, states.c.name, states.c.created_at, states.c.updated_at)
                .where(states.c.user_id == user_id)
                .order_by(states.c.updated_at.desc(), states.c.id.desc())
            )
            return [
                StateSummary(row.id, row.name, _utc(row.created_at), _utc(row.updated_at))
                for row in rows
            ]

        return self._read(run)

    def create_state(
        self,
        user_id: int,
        name: str,
        configuration: dict[str, Any] | None,
        schedules: dict[str, Any] | None,
    ) -> SavedState:
        def run(connection) -> SavedState:
            now = self._clock()
            result = connection.execute(
                insert(states).values(
                    user_id=user_id,
                    name=name,
                    configuration=configuration,
                    schedules=schedules,
                    created_at=now,
                    updated_at=now,
                )
            )
            state_id = int(result.inserted_primary_key[0])
            return SavedState(state_id, user_id, name, configuration, schedules, now, now)

        try:
            return self._write(run)
        except IntegrityError:
            raise StateNameTaken(f"You already have a state named {name!r}.") from None

    def get_state(self, user_id: int, state_id: int) -> SavedState | None:
        def run(connection) -> SavedState | None:
            row = connection.execute(
                select(states).where(states.c.id == state_id, states.c.user_id == user_id)
            ).first()
            if row is None:
                return None
            return SavedState(
                row.id,
                row.user_id,
                row.name,
                row.configuration,
                row.schedules,
                _utc(row.created_at),
                _utc(row.updated_at),
            )

        return self._read(run)

    def save_state(
        self,
        user_id: int,
        state_id: int,
        configuration: dict[str, Any] | None,
        schedules: dict[str, Any] | None,
    ) -> datetime:
        def run(connection) -> datetime:
            now = self._clock()
            result = connection.execute(
                update(states)
                .where(states.c.id == state_id, states.c.user_id == user_id)
                .values(configuration=configuration, schedules=schedules, updated_at=now)
            )
            if result.rowcount == 0:
                raise StateNotFound()
            return now

        return self._write(run)

    def rename_state(self, user_id: int, state_id: int, name: str) -> None:
        def run(connection) -> None:
            result = connection.execute(
                update(states)
                .where(states.c.id == state_id, states.c.user_id == user_id)
                .values(name=name)
            )
            if result.rowcount == 0:
                raise StateNotFound()

        try:
            self._write(run)
        except IntegrityError:
            raise StateNameTaken(f"You already have a state named {name!r}.") from None

    def delete_state(self, user_id: int, state_id: int) -> None:
        def run(connection) -> None:
            result = connection.execute(
                delete(states).where(states.c.id == state_id, states.c.user_id == user_id)
            )
            if result.rowcount == 0:
                raise StateNotFound()
            connection.execute(
                update(users)
                .where(users.c.id == user_id, users.c.last_state_id == state_id)
                .values(last_state_id=None)
            )

        self._write(run)

    # --------------------------------------------------------------- internals

    def _read(self, work: Callable[[Any], T]) -> T:
        self._ensure_schema()
        try:
            with self._engine.connect() as connection:
                return work(connection)
        except SQLAlchemyError as error:
            logger.warning("Account database read failed: %s", type(error).__name__)
            raise StorageFailed(UNREACHABLE) from error

    def _write(self, work: Callable[[Any], T]) -> T:
        """Run ``work`` in one transaction. Integrity errors are re-raised for the caller to
        explain; other database errors become :class:`StorageFailed`."""
        self._ensure_schema()
        try:
            with self._engine.begin() as connection:
                return work(connection)
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.warning("Account database write failed: %s", type(error).__name__)
            raise StorageFailed(UNREACHABLE) from error

    def _ensure_schema(self) -> None:
        if self._ready:
            return
        with self._ready_lock:
            if self._ready:
                return
            try:
                metadata.create_all(self._engine)
            except SQLAlchemyError as error:
                logger.warning("Account database setup failed: %s", type(error).__name__)
                raise StorageFailed(UNREACHABLE) from error
            self._ready = True


def _utc(moment: datetime) -> datetime:
    """SQLite returns times without a zone; they were written in UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
