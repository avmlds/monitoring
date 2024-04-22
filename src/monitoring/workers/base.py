import logging

from monitoring.config import Config
from monitoring.database import LocalDatabaseManager

LOG = logging.getLogger()


class BaseWorker:
    """Base class for an async worker."""

    def __init__(self, config: Config, database_manager: LocalDatabaseManager) -> None:
        self.config = config
        self.database_manager = database_manager

    @classmethod
    def class_name(cls) -> str:
        return cls.__name__

    async def start(self) -> None:
        raise NotImplementedError


class Worker(BaseWorker):
    async def _task(self) -> None:
        raise NotImplementedError

    async def worker(self) -> None:
        while not self.database_manager.is_terminating:
            await self._task()

    async def start(self) -> None:
        LOG.warning(f"Starting {self.class_name()} worker.")
        await self.worker()
