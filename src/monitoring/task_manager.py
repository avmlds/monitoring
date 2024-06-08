import asyncio
import heapq
import logging
import socket
from typing import List

from monitoring.constants import (
    ALLOWED_TIME_ERROR_SECONDS,
    DEFAULT_BATCH_SIZE,
    EXPORT_INTERVAL_SECONDS,
    MAX_RECONNECTION_ATTEMPTS,
)
from monitoring.exceptions import ConnectionAttemptsExceededError
from monitoring.models import HealthcheckConfig, ServiceResponse
from monitoring.repositories import BaseRepository
from monitoring.utils import send_async_request

LOG = logging.getLogger()


class Killswitch:
    def __init__(self) -> None:
        self.value = False

    def engage(self) -> None:
        self.value = True

    @property
    def engaged(self) -> bool:
        return self.value


class BaseWorker:
    """Base class for an async worker."""

    def __init__(self, killswitch: Killswitch):
        self.killswitch = killswitch

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
        while not self.killswitch.engaged:
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
        export_interval: int = EXPORT_INTERVAL_SECONDS,
    ) -> None:
        counter = 0
        elements: List[ServiceResponse] = []
        while not self.killswitch.engaged or not result_queue.empty():
            # not result_queue.empty() - to drain result queue before shutting down.
            if len(elements) == 0:
                elements = await self.load_batch(result_queue, batch_size)
            try:
                await self.export(database, elements)
                LOG.info(f"Exported {len(elements)} elements.")
                elements = []
                counter = 0
            except (ConnectionError, socket.gaierror):
                if counter > MAX_RECONNECTION_ATTEMPTS:
                    raise ConnectionAttemptsExceededError
                LOG.error("Connection failed. Trying to reconnect")
                counter += 1
                await database.reconnect()
            except Exception as unforeseen_consequences:
                self.killswitch.engage()
                LOG.exception("Unexpected error. Terminating.", exc_info=unforeseen_consequences)
                break

            if not self.killswitch.engaged:
                await asyncio.sleep(export_interval)

    async def start(
        self,
        database: BaseRepository,
        result_queue: asyncio.Queue[ServiceResponse],
        batch_size: int = DEFAULT_BATCH_SIZE,
        export_interval: int = EXPORT_INTERVAL_SECONDS,
    ) -> None:
        connection = None
        try:
            connection = await database.connect()
            await self.export_rows(connection, result_queue, batch_size, export_interval)
        except Exception as e:
            LOG.error(
                f"Failed to export data to an external database. Application will be shut down. Reason: {e}",
            )
            self.killswitch.engage()
        finally:
            if connection is not None:
                await connection.disconnect()
