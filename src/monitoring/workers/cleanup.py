import asyncio
import logging

from monitoring.workers.base import Worker

LOG = logging.getLogger()


class Collector(Worker):
    """Garbage collector.

    Responsible for deleting processed records from a local database.
    """

    PAUSE_TIME_SECONDS = 2

    async def _task(self) -> None:
        loop = asyncio.get_running_loop()
        before = await loop.run_in_executor(None, self.database_manager.count_processed)
        LOG.debug(f"Found {before} processed records to delete.")
        if before != 0:
            await loop.run_in_executor(None, self.database_manager.delete_processed)
            LOG.info(f"{before} processed records deleted.")
        await asyncio.sleep(self.PAUSE_TIME_SECONDS)
