import asyncio
import copy
import heapq
import logging
import os
from typing import List, Tuple

from monitoring.config import Config, StartupConfiguration
from monitoring.exceptions import (
    InvalidDatabaseUriError,
    NoServicesSpecifiedError,
)
from monitoring.models import HealthcheckConfig, ServiceResponse
from monitoring.repositories import PostgresRepository
from monitoring.task_manager import Agent, Exporter, Killswitch

LOG = logging.getLogger()


def estimate_workload(config: Config) -> Tuple[float, float]:
    """Estimate workload in RPM (requests per minute)."""

    rpm = [1 / service.interval_sec for service in config.services]
    total_rps = sum(rpm)
    avg = total_rps / len(config.services)
    LOG.warning(f"Average requests per second (RPS) across all services: {avg:.2f}")
    LOG.warning(f"Total requests per second (RPS) across all services: {total_rps:.2f}")
    return total_rps, avg


async def start_workers(
    services: List[HealthcheckConfig],
    external_database_uri: str,
    export_batch_size: int,
    export_interval: int,
    killswitch: Killswitch,
) -> None:
    """Start all the application workers."""

    q_size = len(services)

    task_queue = copy.deepcopy(services)
    heapq.heapify(task_queue)
    result_queue: asyncio.Queue[ServiceResponse] = asyncio.Queue(maxsize=q_size)

    monitoring = Agent(killswitch)
    exporter = Exporter(killswitch)

    database = PostgresRepository(external_database_uri)
    await asyncio.gather(
        monitoring.start(task_queue, result_queue),
        exporter.start(database, result_queue, export_batch_size, export_interval),
    )


def _start(
    services: List[HealthcheckConfig],
    external_database_uri: str,
    export_batch_size: int,
    export_interval: int,
) -> None:
    killswitch = Killswitch()
    try:
        asyncio.run(
            start_workers(
                services,
                external_database_uri,
                export_batch_size,
                export_interval,
                killswitch,
            )
        )
    except KeyboardInterrupt:
        LOG.warning("Killswitch engaged. Shutting down the application.")
        killswitch.engage()


def start(startup_configuration: StartupConfiguration) -> None:
    """Application's entrypoint."""

    external_database_uri = os.getenv("DATABASE_URI")
    if not external_database_uri:
        raise InvalidDatabaseUriError

    config = Config.load(startup_configuration.config_path)
    if config.contains_no_service:
        raise NoServicesSpecifiedError

    estimate_workload(config)
    startup_configuration.notify_systemd()
    _start(
        config.services,
        external_database_uri,
        startup_configuration.export_batch_size,
        startup_configuration.export_interval,
    )
