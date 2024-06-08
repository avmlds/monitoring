import json
import logging
import os
import socket
from json import JSONDecodeError
from pathlib import Path
from typing import List

from prettytable import PrettyTable
from pydantic import BaseModel, model_validator

from monitoring.constants import (
    DEBUG_LEVEL,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CONFIG_PATH,
    DEFAULT_VERBOSITY_LEVEL,
    ERROR_LEVEL,
    EXPORT_INTERVAL_SECONDS,
    INFO_LEVEL,
    MAX_BATCH_SIZE,
    MAX_EXPORT_INTERVAL_SECONDS,
    MIN_BATCH_SIZE,
    MIN_EXPORT_INTERVAL_SECONDS,
    SYSTEMD_NOTIFY_MESSAGE,
    SYSTEMD_SOCKET,
    WARNING_LEVEL,
)
from monitoring.exceptions import InvalidBatchSizeError, InvalidConfigurationFileError, InvalidExportIntervalError
from monitoring.models import HealthcheckConfig
from monitoring.utils import check_path_existence

LOG = logging.getLogger()


class Config(BaseModel):
    """Global util configuration."""

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


class StartupConfiguration(BaseModel):
    """Class for startup configurations."""

    verbosity_level: int = DEFAULT_VERBOSITY_LEVEL
    config_path: Path = Path(DEFAULT_CONFIG_PATH)
    systemd_notify: bool = False
    export_batch_size: int = DEFAULT_BATCH_SIZE
    export_interval: int = EXPORT_INTERVAL_SECONDS

    @model_validator(mode="after")
    def validate_export_batch_size(self) -> "StartupConfiguration":
        if self.export_batch_size < MIN_BATCH_SIZE or self.export_batch_size > MAX_BATCH_SIZE:
            raise InvalidBatchSizeError
        return self

    @model_validator(mode="after")
    def validate_export_interval(self) -> "StartupConfiguration":
        if self.export_interval < MIN_EXPORT_INTERVAL_SECONDS or self.export_interval > MAX_EXPORT_INTERVAL_SECONDS:
            raise InvalidExportIntervalError
        return self

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
