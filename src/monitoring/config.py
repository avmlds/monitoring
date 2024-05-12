import json
import logging
import os
import socket
from json import JSONDecodeError
from pathlib import Path
from typing import List

from prettytable import PrettyTable
from pydantic import BaseModel

from monitoring.constants import (
    DEBUG_LEVEL,
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAX_WORKERS,
    DEFAULT_VERBOSITY_LEVEL,
    ERROR_LEVEL,
    INFO_LEVEL,
    MAX_SERVICES_PER_WORKER,
    SYSTEMD_NOTIFY_MESSAGE,
    SYSTEMD_SOCKET,
    WARNING_LEVEL,
)
from monitoring.exceptions import InvalidConfigurationFileError
from monitoring.models import HealthcheckConfig
from monitoring.utils import check_path_existence

LOG = logging.getLogger()


class Config(BaseModel):
    """Global util configuration."""

    local_database_path: str
    external_database_uri: str
    services: List[HealthcheckConfig]

    @property
    def contains_no_service(self) -> bool:
        return len(self.services) == 0

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """Load configuration file from a file."""
        path = config_path.expanduser().absolute()
        check_path_existence(path)
        try:
            with path.open("r") as f:
                config = json.load(f)
        except JSONDecodeError:
            raise InvalidConfigurationFileError(path.as_posix())

        # external_database_uri = os.getenv("RAM_DATABASE_URI")
        # config["external_database_uri"] = external_database_uri
        return cls(**config)

    @staticmethod
    def _create_if_not_exists(config_path: Path) -> None:
        if not config_path.exists():
            os.makedirs(config_path.parent, exist_ok=True)
            config_path.touch()

    def dump(self, path: Path) -> None:
        """Save (dump) configuration file on a disk."""
        config_path = path.expanduser().absolute()
        self._create_if_not_exists(config_path)
        with config_path.open("w") as f:
            json.dump(self.model_dump(), f)

    @property
    def sorted_services(self) -> List[HealthcheckConfig]:
        return sorted(self.services, key=lambda service: service.sorting_helper)

    def services_table(self, numbered: bool = False) -> PrettyTable:
        """Visualise configured services."""
        headers = HealthcheckConfig.fields()
        table_headers = headers
        if numbered:
            table_headers = ["№", *headers]
        table = PrettyTable(field_names=table_headers)
        for n, service in enumerate(self.sorted_services):
            row = [getattr(service, header_name) for header_name in headers]
            if numbered:
                row = [n] + row
            table.add_row(row)
        return table

    def databases_table(self) -> PrettyTable:
        """Visualise configured databases."""
        headers = ("Name", "Value")
        table = PrettyTable(field_names=headers)
        table.add_row(("Local", self.local_database_path))
        table.add_row(("External", self.external_database_uri))
        return table


class StartupConfiguration(BaseModel):
    """Class for startup configurations."""

    max_workers: int = DEFAULT_MAX_WORKERS
    services_per_worker: int = MAX_SERVICES_PER_WORKER
    verbosity_level: int = DEFAULT_VERBOSITY_LEVEL
    config_path: Path = Path(DEFAULT_CONFIG_PATH)
    systemd_notify: bool = False

    @property
    def logging_level(self) -> int:
        """Calculate logging level."""
        if self.verbosity_level >= DEBUG_LEVEL:
            return logging.DEBUG
        elif self.verbosity_level == INFO_LEVEL:
            return logging.INFO
        elif self.verbosity_level == WARNING_LEVEL:
            return logging.WARNING
        elif self.verbosity_level == ERROR_LEVEL:
            return logging.ERROR
        else:
            return logging.CRITICAL

    def notify_systemd(self) -> None:
        """Send a message to systemd socket if necessary."""
        if not self.systemd_notify:
            LOG.warning("Systemd notification is disabled.")
        else:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            s.connect(SYSTEMD_SOCKET)
            s.sendall(SYSTEMD_NOTIFY_MESSAGE)
            s.close()
            LOG.warning("Systemd was notified. We are ready to rock!")
