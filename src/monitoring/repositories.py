import logging
from abc import ABC, abstractmethod
from typing import Any, List, Tuple

import asyncpg  # type: ignore[import-untyped]
from typing_extensions import Self

from monitoring.models import ServiceResponse

LOG = logging.getLogger()


class BaseRepository(ABC):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @abstractmethod
    async def connect(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reconnect(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def create(self, items: List[ServiceResponse]) -> None:
        raise NotImplementedError


class PostgresRepository(BaseRepository):
    def __init__(self, dsn: str) -> None:
        super().__init__(dsn)
        self.pool = None

    CREATE_REMOTE_MONITORING_TABLE = (
        "CREATE TABLE IF NOT EXISTS monitoring ("
        "    id SERIAL PRIMARY KEY,"
        "    url VARCHAR NOT NULL,"
        "    method VARCHAR NOT NULL,"
        "    request_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,"
        "    regex_check_required BOOLEAN NOT NULL,"
        "    contains_regex BOOLEAN NOT NULL,"
        "    contains_exception BOOLEAN NOT NULL,"
        "    status_code INTEGER,"
        "    response_timestamp TIMESTAMP WITH TIME ZONE,"
        "    regex VARCHAR,"
        "    exception TEXT,"
        "    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (timezone('utc', now()))"
        ");"
    )
    """Create a monitoring table in a remote database. Won't recreate a table if it exists."""

    INSERT_REMOTE_MONITORING_TABLE = (
        "INSERT INTO monitoring ("
        "    url,"
        "    method,"
        "    request_timestamp,"
        "    regex_check_required,"
        "    contains_regex,"
        "    contains_exception,"
        "    status_code,"
        "    response_timestamp,"
        "    regex,"
        "    exception"
        ") VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);"
    )
    """Insert a row into a remote database. If row was already inserted - does nothing."""

    async def connect(self) -> Self:
        """Establish connection to a remote database."""

        if self.pool is None:
            LOG.debug("Creating connection to a remote database.")
            pool = await asyncpg.create_pool(self.dsn, min_size=1)
            async with pool.acquire() as connection:
                await connection.execute(self.CREATE_REMOTE_MONITORING_TABLE)
                LOG.debug("Connection to a remote database was successfully established.")
            self.pool = pool
        return self

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    async def reconnect(self) -> Self:
        if self.pool is not None:
            self.pool.terminate()
            self.pool = None
        return await self.connect()

    @staticmethod
    def _item_as_row(item: ServiceResponse) -> Tuple[Any, ...]:
        return (
            item.url,
            item.method,
            item.request_timestamp,
            item.regex_check_required,
            item.contains_regex,
            item.contains_exception,
            item.status_code,
            item.response_timestamp,
            item.regex,
            item.exception,
        )

    async def create(self, items: List[ServiceResponse]) -> None:
        rows = [self._item_as_row(item) for item in items]
        if self.pool is not None:
            async with self.pool.acquire() as connection:
                await connection.executemany(self.INSERT_REMOTE_MONITORING_TABLE, rows)
            LOG.debug(f"Exported {len(rows)} records.")
        else:
            raise ConnectionError
