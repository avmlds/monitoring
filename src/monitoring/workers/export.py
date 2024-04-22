import asyncio
import logging
import socket
from typing import Any, Dict, Iterable, List, Optional, Tuple

import asyncpg  # type: ignore

from monitoring.config import Config
from monitoring.database import LocalDatabaseManager
from monitoring.models import ServiceResponseLocalDump, ServiceResponseRemoteDump
from monitoring.queries import (
    CREATE_REMOTE_MONITORING_TABLE,
    INSERT_REMOTE_MONITORING_TABLE,
    SELECT_LOCAL_ID_FROM_REMOTE_MONITORING_TABLE,
)
from monitoring.workers.base import Worker

LOG = logging.getLogger()


class Exporter(Worker):
    """Worker-exporter.

    Responsible for sending monitoring logs to an external database."""

    SLEEP_TIME_SECONDS = 1

    def __init__(self, config: Config, database_manager: LocalDatabaseManager) -> None:
        super().__init__(config, database_manager)
        self.pool: Optional[asyncpg.Pool] = None

    @staticmethod
    async def _get_pool(database_uri: str) -> asyncpg.Pool:
        pool = await asyncpg.create_pool(database_uri, min_size=1)
        async with pool.acquire() as connection:
            await connection.execute(CREATE_REMOTE_MONITORING_TABLE)
        return pool

    async def get_pool(self) -> asyncpg.Pool:
        LOG.debug("Creating connection to a remote database.")
        if self.pool is None:
            self.pool = await self._get_pool(self.config.external_database_uri)
            LOG.debug("Connection to a remote database was successfully established.")
        return self.pool

    @staticmethod
    def prepare_select_inserted_query(rows_to_insert: List[Tuple[Any, ...]]) -> str:
        placeholders = ", ".join([f"${i + 1}" for i in range(len(rows_to_insert))])
        return SELECT_LOCAL_ID_FROM_REMOTE_MONITORING_TABLE.format(placeholders)

    async def _export_rows(self, dumped_rows: List[ServiceResponseLocalDump]) -> None:
        loop = asyncio.get_event_loop()

        rows_for_export = [ServiceResponseRemoteDump.from_local_dump(dumped_row).as_row() for dumped_row in dumped_rows]
        local_ids = [row[0] for row in rows_for_export]
        select_query = self.prepare_select_inserted_query(rows_for_export)

        pool = await self.get_pool()
        async with pool.acquire() as connection:
            await connection.executemany(INSERT_REMOTE_MONITORING_TABLE, rows_for_export)
            result = await connection.fetch(select_query, *local_ids)

        processed_ids = [row["local_id"] for row in result]
        await loop.run_in_executor(None, self.database_manager.mark_as_processed, processed_ids)
        LOG.info(f"Exported {len(processed_ids)} records.")

    async def _task(self, *args: Iterable[Any], **kwargs: Dict[str, Any]) -> None:
        try:
            loop = asyncio.get_event_loop()
            dumped_rows = await loop.run_in_executor(None, self.database_manager.load_unprocessed)
            if not dumped_rows:
                LOG.info("No records to export.")
            else:
                LOG.info(f"Trying to export {len(dumped_rows)} records to an external database.")
                await self._export_rows(dumped_rows)
        except (ConnectionRefusedError, ConnectionError, ConnectionResetError, ConnectionAbortedError, socket.gaierror) as e:
            exception = None
            if self.pool is not None:
                exception = e
                self.pool.terminate()
                self.pool = None
            LOG.exception(
                "Can't connect to an external database. System will try to reconnect later.",
                exc_info=exception,
            )
        await asyncio.sleep(self.SLEEP_TIME_SECONDS)
