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
        """Logging helper for returning class name."""
        return cls.__name__

    async def start(self) -> None:
        """Main worker method."""
        raise NotImplementedError


class Worker(BaseWorker):
    """Base class for a worker."""

    async def _task(self) -> None:
        """Worker task that will be called in an infinite loop."""
        raise NotImplementedError

    async def worker(self) -> None:
        """Base worker task loop."""
        while not self.database_manager.is_terminating:
            await self._task()

    async def start(self) -> None:
        LOG.warning(f"Starting {self.class_name()} worker.")
        await self.worker()
