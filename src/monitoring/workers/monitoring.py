import asyncio
import logging
from typing import Tuple

from monitoring.constants import MINUTE_SECONDS
from monitoring.models import HealthcheckConfig
from monitoring.utils import send_async_request
from monitoring.workers.base import BaseWorker

LOG = logging.getLogger()


class Agent(BaseWorker):
    def estimate_workload(self) -> Tuple[float, float]:
        rpm = [MINUTE_SECONDS / service.interval_sec for service in self.config.services]
        total_rpm = sum(rpm)
        avg = total_rpm / len(self.config.services)
        LOG.warning(f"Average requests per minute (RPM) across all services: {avg:.2f}")
        LOG.warning(f"Total requests per minute (RPM) across all services: {total_rpm:.2f}")
        return total_rpm, avg

    async def _task(self, config: HealthcheckConfig) -> None:
        service_response = await send_async_request(
            config.method,
            config.url,
            regex_check_required=config.check_regex,
            regex=config.regex,
            timeout=config.timeout,
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.database_manager.dump, service_response)
        LOG.debug(f"Response {service_response} was dumped to a local database.")
        await asyncio.sleep(config.interval_sec)

    async def worker(self, config: HealthcheckConfig) -> None:
        while not self.database_manager.is_terminating:
            await self._task(config)

    async def start(self) -> None:
        LOG.warning(f"Starting {self.class_name()} worker.")
        self.estimate_workload()
        await asyncio.gather(*map(self.worker, self.config.services))
