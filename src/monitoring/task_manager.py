import asyncio
import heapq
import logging
import socket
from typing import List

from monitoring.constants import ALLOWED_TIME_ERROR_SECONDS, DEFAULT_BATCH_SIZE, MAX_RECONNECTION_ATTEMPTS
from monitoring.exceptions import ConnectionAttemptsExceededError
from monitoring.models import HealthcheckConfig, ServiceResponse
from monitoring.repositories import BaseRepository
from monitoring.utils import send_async_request

LOG = logging.getLogger()


class BaseWorker:
    """Base class for an async worker."""

    @classmethod
    def class_name(cls) -> str:
        """Logging helper for returning class name."""
        return cls.__name__


class Agent(BaseWorker):
    """Main agent that takes care about sending HTTP requests to specified services."""

    async def start(
        self,
        task_queue: List[HealthcheckConfig],
        result_queue: asyncio.Queue[ServiceResponse],
    ) -> None:
        """Main worker method."""

        LOG.debug(f"Starting {self.class_name()} worker.")
        while True:
            config: HealthcheckConfig = heapq.heappop(task_queue)
            p1_priority = config.priority_seconds
            if p1_priority > 0:
                await asyncio.sleep(p1_priority)

            result = await send_async_request(
                config.method,
                config.url,
                regex_check_required=config.check_regex,
                regex=config.regex,
                timeout=config.timeout,
            )

            if config.last_checked_at is not None:
                elapsed = (result.request_timestamp - config.last_checked_at).total_seconds()
                if elapsed > (config.interval_sec + ALLOWED_TIME_ERROR_SECONDS):
                    LOG.error(
                        f"Increase number of application instances. "
                        f"Task executed for too long: '{elapsed}' instead of '{config.interval_sec}'"
                    )
            config.last_checked_at = result.response_timestamp
            await result_queue.put(result)
            heapq.heappush(task_queue, config)


class Exporter(BaseWorker):
    """Worker-exporter.

    Responsible for sending monitoring logs to an external database."""

    SLEEP_TIME_SECONDS = 5

    @staticmethod
    async def load_batch(result_queue: asyncio.Queue[ServiceResponse], batch_size: int) -> List[ServiceResponse]:
        batch: List[ServiceResponse] = []
        while not result_queue.empty() and len(batch) < batch_size:
            element = await result_queue.get()
            batch.append(element)
        return batch

    @staticmethod
    async def export(database: BaseRepository, batch: List[ServiceResponse]) -> None:
        await database.create(batch)

    async def export_rows(
        self,
        database: BaseRepository,
        result_queue: asyncio.Queue[ServiceResponse],
        batch_size: int,
    ) -> None:
        counter = 0
        elements: List[ServiceResponse] = []
        while True:
            if len(elements) == 0:
                elements = await self.load_batch(result_queue, batch_size)
            try:
                await self.export(database, elements)
                LOG.warning(f"Exported {len(elements)} elements.")
                elements = []
                counter = 0
            except (ConnectionError, socket.gaierror):
                if counter > MAX_RECONNECTION_ATTEMPTS:
                    raise ConnectionAttemptsExceededError
                LOG.error("Connection failed. Trying to reconnect")
                counter += 1
                await database.reconnect()
            except Exception as unforeseen_consequences:
                LOG.exception("Unexpected error. Terminating.")
                raise Exception from unforeseen_consequences
            await asyncio.sleep(self.SLEEP_TIME_SECONDS)

    async def start(
        self,
        database: BaseRepository,
        result_queue: asyncio.Queue[ServiceResponse],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        connection = await database.connect()
        try:
            await self.export_rows(connection, result_queue, batch_size)
        finally:
            await connection.disconnect()
