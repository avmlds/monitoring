#!/usr/bin/env python3
import logging
import os
from pathlib import Path
from typing import Optional

import click

from monitoring.config import Config, StartupConfiguration
from monitoring.constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOCALDB_PATH,
    DEFAULT_MAX_WORKERS,
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    MAX_HEALTHCHECK_INTERVAL_SECONDS,
    MAX_SERVICES_PER_WORKER,
    MIN_HEALTHCHECK_INTERVAL_SECONDS,
    SUPPORTED_METHODS,
)
from monitoring.execution import start
from monitoring.models import HealthcheckConfig
from monitoring.utils import check_path_existence

logger = logging.getLogger()
logging.getLogger("aiohttp").setLevel("CRITICAL")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s | %(asctime)s | %(module)s | %(lineno)d | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


@click.group()
def cli() -> None:
    """Universal http/https monitoring tool."""


@cli.group()
def config() -> None:
    """Manage monitoring configuration."""


@click.option("--local-path", default=Path(DEFAULT_LOCALDB_PATH), type=Path)
@click.argument("external-uri")
@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@config.command("create")
def create_config(local_path: Path, external_uri: str, config_path: Path) -> None:
    """Create configuration file."""

    database_path = local_path.expanduser().absolute().as_posix()
    configuration = Config(local_database_path=database_path, external_database_uri=external_uri, services=[])
    configuration.dump(config_path)
    print(f"Configuration was successfully created at '{config_path.expanduser().absolute().as_posix()}'.")
    print("Now you can add your first service configuration with 'monitor config services add'")


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@config.command("delete")
def delete_config(config_path: Path) -> None:
    """Delete configuration file."""

    path = config_path.expanduser().absolute()
    click.confirm(f"Are you sure want to delete configuration file at '{path.as_posix()}'?", abort=True)
    check_path_existence(path)
    os.remove(path)


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@config.command("show")
def show_config(config_path: Path) -> None:
    """Show configuration."""

    configuration = Config.load(config_path)
    print(configuration.databases_table())
    print(configuration.services_table())


@config.group()
def databases() -> None:
    """Manage database configuration."""


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@databases.command("show")
def show_database_configuration(config_path: Path) -> None:
    """Manage database configuration."""

    configuration = Config.load(config_path)
    print(configuration.databases_table())


@click.option("--local-path", type=Path)
@click.option("--external-uri")
@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@databases.command("update")
def update_database_configuration(local_path: Optional[Path], external_uri: str, config_path: Path) -> None:
    """Update database configuration."""

    if not local_path and not external_uri:
        return
    configuration = Config.load(config_path)

    configuration_changed = False
    if local_path is not None:
        check_path_existence(local_path)
        configuration_changed = True
        configuration.local_database_path = local_path.expanduser().absolute().as_posix()

    if external_uri:
        configuration_changed = True
        configuration.external_database_uri = external_uri

    if configuration_changed:
        configuration.dump(config_path)


@config.group()
def services() -> None:
    """Manage services configuration."""


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@click.option("--numbered", is_flag=True)
@services.command("show")
def show_services_configuration(numbered: bool, config_path: Path) -> None:
    """Show configured services."""

    configuration = Config.load(config_path)
    print(configuration.services_table(numbered))


@click.option("--quiet", "-q", is_flag=True, help="Disable output.")
@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@click.option(
    "--interval",
    type=int,
    default=DEFAULT_REQUEST_INTERVAL_SECONDS,
    help="Interval in seconds between requests. Must be between 5 and 300.",
)
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    help="Timeout for outgoing connections to a service.",
)
@click.option("--regex", help="Regexp to check.")
@click.option("--check-regex", is_flag=True, help="Check request text against a certain regexp.")
@click.argument("method", type=click.Choice(SUPPORTED_METHODS))
@click.argument("url")
@services.command("add")
def add_service_configuration(
    url: str,
    method: str,
    regex: Optional[str],
    check_regex: bool,
    interval: int,
    timeout: int,
    config_path: Path,
    quiet: bool,
) -> None:
    """Add new service to the configuration."""

    configuration = Config.load(config_path)
    service = HealthcheckConfig(
        url=url,
        method=method,
        regex=regex,
        check_regex=check_regex,
        interval_sec=interval,
        timeout=timeout,
    )
    if service in configuration.services:
        raise click.UsageError("Service with specified parameters already exists.")

    configuration.services.append(service)
    configuration.dump(config_path)
    if not quiet:
        print(configuration.services_table())
        print("Service was successfully added. Restart application.")


@click.option("--quiet", "-q", is_flag=True, help="Disable output.")
@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@click.argument("number", type=int)
@services.command("remove")
def remove_service_configuration(number: int, config_path: Path, quiet: bool) -> None:
    """Remove a service under NUMBER in the configuration.

    To get a number, run `monitor config services show --numbered`"""

    configuration = Config.load(Path(config_path))
    services_total = len(configuration.services)
    if services_total == 0:
        raise click.UsageError("Add service first.")

    if number < 0 or number >= services_total:
        raise click.BadArgumentUsage(f"Invalid argument value. Must me between 0 and {services_total}")

    service_to_remove = configuration.sorted_services[number]
    click.confirm(f"Are you sure want to remove Service({service_to_remove})?", abort=True)

    configuration.services = [service for service in configuration.services if service != service_to_remove]
    configuration.dump(config_path)
    if not quiet:
        print(configuration.services_table())
        print("Service was successfully removed. Restart application.")


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@click.option("--interval", type=int, help="Interval in seconds between requests. Must be between 5 and 300.")
@click.option("--timeout", type=int, help="Timeout for outgoing connections to a service.")
@click.option("--regex", help="Regexp to check.")
@click.option("--toggle-check-regex", is_flag=True, help="Toggle regex checking mode.")
@click.argument("number", type=int)
@services.command("update")
def update_service_configuration(
    number: int,
    regex: Optional[str],
    toggle_check_regex: bool,
    interval: Optional[int],
    timeout: Optional[int],
    config_path: Path,
) -> None:
    """Update service under NUMBER in the configuration.

    To get a number, run `monitor config services show --numbered`
    """

    configuration = Config.load(Path(config_path))
    services_total = len(configuration.services)
    if services_total == 0:
        raise click.UsageError("Add service first.")

    if number < 0 or number >= services_total:
        raise click.BadArgumentUsage(f"Invalid argument value. Must me between 0 and {services_total}")

    if timeout is not None and timeout <= 0:
        raise click.BadArgumentUsage("Invalid argument value. Must greater than 0.")

    if interval is not None and not (MIN_HEALTHCHECK_INTERVAL_SECONDS <= interval <= MAX_HEALTHCHECK_INTERVAL_SECONDS):
        raise click.BadArgumentUsage(
            f"Invalid argument value. "
            f"Must me between {MIN_HEALTHCHECK_INTERVAL_SECONDS} and {MAX_HEALTHCHECK_INTERVAL_SECONDS}"
        )

    service_to_update = configuration.sorted_services[number]
    click.confirm(f"Are you sure want to update Service({service_to_update})?", abort=True)

    if regex is not None:
        service_to_update.regex = regex
    if toggle_check_regex:
        if service_to_update.regex is None:
            raise click.BadArgumentUsage("You must specify a regex to enable regexp check.")
        service_to_update.check_regex = not service_to_update.check_regex

    if interval is not None:
        service_to_update.interval_sec = interval

    if timeout is not None:
        service_to_update.timeout = timeout

    configuration.dump(config_path)
    print(configuration.services_table())
    print("Service was successfully updated. Restart application.")


@click.option("--config-path", default=Path(DEFAULT_CONFIG_PATH), type=Path, help="Path to the configuration file.")
@click.option("--yes", is_flag=True, help="Start without a confirmation prompt.")
@click.option("--notify-systemd", "-ns", is_flag=True, help="Notify systemd after application start.")
@click.option(
    "--max-workers",
    "-mw",
    type=int,
    default=DEFAULT_MAX_WORKERS,
    help="Max number of workers.",
)
@click.option(
    "--services-per-worker",
    "-spw",
    type=int,
    default=MAX_SERVICES_PER_WORKER,
    help="Max services per worker.",
)
@click.option("-v", count=True, help="Logging level.")
@cli.command("start")
def start_monitoring(
    yes: bool,
    config_path: Path,
    v: int,
    notify_systemd: bool,
    max_workers: int,
    services_per_worker: int,
) -> None:
    """Start monitoring."""

    path = config_path.expanduser().absolute()
    if not yes:
        click.confirm(f"Are you sure want to start monitoring? Config path: {path.as_posix()}", abort=True)
    startup_config = StartupConfiguration(
        verbosity_level=v,
        config_path=config_path,
        systemd_notify=notify_systemd,
        max_workers=max_workers,
        services_per_worker=services_per_worker,
    )
    logger.setLevel(startup_config.logging_level)
    start(startup_config)
