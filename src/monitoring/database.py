import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Iterator, List, cast

from monitoring.models import ServiceResponse, ServiceResponseLocalDump
from monitoring.queries import (
    COUNT_PROCESSED,
    CREATE_LOCAL_MONITORING_RECORD,
    CREATE_LOCAL_MONITORING_TABLE,
    DELETE_PROCESSED,
    MARK_AS_PROCESSED,
    SELECT_UNPROCESSED,
)


class LocalDatabaseManager:
    """Connection manager.

    Abstraction for a local SQLite database."""

    _LOCK = threading.Lock()

    def __init__(self, path: Path, connection: sqlite3.Connection):
        self.path = path
        self.connection = connection
        self.is_terminating = False

    @classmethod
    @contextlib.contextmanager
    def connect(cls, db_path: str) -> Iterator["LocalDatabaseManager"]:
        """Context manager that yields a class instance with initialized
        connection to a local SQLite database."""

        path = Path(db_path).expanduser().absolute()
        connection = sqlite3.connect(path.as_posix(), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        klass = cls(path, connection)
        try:
            yield klass
        except (KeyboardInterrupt, SystemExit):
            with klass._LOCK:
                klass.is_terminating = True
        finally:
            connection.close()

    def init(self) -> None:
        """Initial idempotent create for a monitoring table."""

        self.connection.execute(CREATE_LOCAL_MONITORING_TABLE)
        self.connection.commit()

    def dump(self, service_response: ServiceResponse) -> None:
        """Create and validate a row and dump it into the local database."""
        to_dump = ServiceResponseLocalDump.from_service_response(service_response)
        with self._LOCK:
            self.connection.execute(CREATE_LOCAL_MONITORING_RECORD, to_dump.model_dump())
            self.connection.commit()

    def _load_rows(self, query: str) -> List[ServiceResponseLocalDump]:
        """Wrapper for fetching rows and turning them into validated objects."""
        cursor = self.connection.execute(query)
        return [ServiceResponseLocalDump(**row) for row in cursor.fetchall()]

    def mark_as_processed(self, ids: List[str]) -> None:
        with self._LOCK:
            # It's not a dangerous string interpolation
            query = MARK_AS_PROCESSED.format(", ".join(["?"] * len(ids)))
            self.connection.execute(query, ids)
            self.connection.commit()

    def load_unprocessed(self) -> List[ServiceResponseLocalDump]:
        return self._load_rows(SELECT_UNPROCESSED)

    def delete_processed(self) -> None:
        with self._LOCK:
            self.connection.execute(DELETE_PROCESSED)
            self.connection.commit()

    def count_processed(self) -> int:
        cursor = self.connection.execute(COUNT_PROCESSED)
        return cast(int, cursor.fetchone()[0])
