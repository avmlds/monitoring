import asyncio

from monitoring.config import Config, StartupConfiguration
from monitoring.database import LocalDatabaseManager
from monitoring.exceptions import NoServicesSpecifiedError
from monitoring.workers import Agent, Collector, Exporter


async def start_workers(
    config: Config,
    manager: LocalDatabaseManager,
) -> None:
    """Start all the application workers."""
    monitoring = Agent(config, manager)
    exporter = Exporter(config, manager)
    collector = Collector(config, manager)
    await asyncio.gather(monitoring.start(), collector.start(), exporter.start())


def start(startup_configuration: StartupConfiguration) -> None:
    """Application's entrypoint."""
    config = Config.load(startup_configuration.config_path)
    if config.contains_no_service:
        raise NoServicesSpecifiedError
    with LocalDatabaseManager.connect(config.local_database_path) as manager:
        manager.init()
        startup_configuration.notify_systemd()
        asyncio.run(start_workers(config, manager))
