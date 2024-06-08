import asyncio
import copy
import heapq
import logging
import multiprocessing
from typing import List, Tuple

from monitoring.config import Config, StartupConfiguration
from monitoring.exceptions import NoServicesSpecifiedError, NotEnoughWorkersError
from monitoring.models import HealthcheckConfig, ServiceResponse
from monitoring.repositories import PostgresRepository
from monitoring.task_manager import Agent, Exporter

LOG = logging.getLogger()


def estimate_workload(config: Config) -> Tuple[float, float]:
    """Estimate workload in RPM (requests per minute)."""

    rpm = [1 / service.interval_sec for service in config.services]
    total_rps = sum(rpm)
    avg = total_rps / len(config.services)
    LOG.warning(f"Average requests per second (RPS) across all services: {avg:.2f}")
    LOG.warning(f"Total requests per second (RPS) across all services: {total_rps:.2f}")
    return total_rps, avg


async def start_workers(services: List[HealthcheckConfig], external_database_uri: str) -> None:
    """Start all the application workers."""

    q_size = len(services)

    task_queue = copy.deepcopy(services)
    heapq.heapify(task_queue)
    result_queue: asyncio.Queue[ServiceResponse] = asyncio.Queue(maxsize=q_size)

    monitoring = Agent()
    exporter = Exporter()

    database = PostgresRepository(external_database_uri)
    await asyncio.gather(monitoring.start(task_queue, result_queue), exporter.start(database, result_queue))


def _start(services: List[HealthcheckConfig], external_database_uri: str) -> None:
    asyncio.run(start_workers(services, external_database_uri))


def start(startup_configuration: StartupConfiguration) -> None:
    """Application's entrypoint."""

    external_database_uri = os.getenv("DATABASE_URI")
    if not external_database_uri:
        raise InvalidDatabaseUriError

    config = Config.load(startup_configuration.config_path)
    if config.contains_no_service:
        raise NoServicesSpecifiedError

    estimate_workload(config)

    max_workers = startup_configuration.max_workers
    service_chunks = [
        config.services[i : i + startup_configuration.services_per_worker]
        for i in range(0, len(config.services), startup_configuration.services_per_worker)
    ]
    if len(service_chunks) != max_workers:
        raise NotEnoughWorkersError(
            max_workers,
            startup_configuration.services_per_worker,
            len(service_chunks),
        )

    if max_workers == 1:
        startup_configuration.notify_systemd()
        _start(config.services, config.external_database_uri)
    else:
        processes = []
        for n in range(max_workers):
            process = multiprocessing.Process(target=_start, args=(service_chunks[n], config.external_database_uri))
            process.start()
            processes.append(process)

        startup_configuration.notify_systemd()
        for p in processes:
            p.join()
