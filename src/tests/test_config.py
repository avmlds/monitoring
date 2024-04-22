import logging
import socket
from pathlib import Path, PosixPath
from unittest import mock
from unittest.mock import MagicMock

import pytest
from prettytable import PrettyTable

from monitoring.config import Config, StartupConfiguration
from monitoring.constants import (
    DEBUG_LEVEL,
    ERROR_LEVEL,
    INFO_LEVEL,
    METHOD_GET,
    METHOD_OPTION,
    METHOD_POST,
    SYSTEMD_NOTIFY_MESSAGE,
    SYSTEMD_SOCKET,
    WARNING_LEVEL,
)
from monitoring.exceptions import PathDoesntExistError
from monitoring.models import HealthcheckConfig


def test_notify_systemd_enabled(mock_socket):
    config = StartupConfiguration(verbosity_level=DEBUG_LEVEL, systemd_notify=True)
    config.notify_systemd()
    mock_socket.assert_called_once_with(socket.AF_UNIX, socket.SOCK_DGRAM)
    mock_socket_instance = mock_socket.return_value
    mock_socket_instance.connect.assert_called_once_with(SYSTEMD_SOCKET)
    mock_socket_instance.sendall.assert_called_once_with(SYSTEMD_NOTIFY_MESSAGE)
    mock_socket_instance.close.assert_called_once()


def test_notify_systemd_disabled(mock_socket):
    config = StartupConfiguration(systemd_notify=False)
    config.notify_systemd()
    mock_socket.assert_not_called()


@pytest.mark.parametrize(
    ("input_level", "output_level"),
    [
        (999, logging.DEBUG),
        (DEBUG_LEVEL, logging.DEBUG),
        (INFO_LEVEL, logging.INFO),
        (WARNING_LEVEL, logging.WARNING),
        (ERROR_LEVEL, logging.ERROR),
        (-1, logging.CRITICAL),
    ],
)
def test_logging_level_debug(input_level, output_level):
    config = StartupConfiguration(verbosity_level=input_level)
    assert config.logging_level == output_level


def test_contains_no_service_true():
    config = Config(local_database_path="", external_database_uri="", services=[])
    assert config.contains_no_service is True


def test_contains_no_service_false():
    config = Config(
        local_database_path="",
        external_database_uri="",
        services=[
            HealthcheckConfig(
                url="https://localhost",
                method=METHOD_POST,
                check_regex=False,
            )
        ],
    )
    assert config.contains_no_service is False


def test_load_config_path_doesnt_exist():
    with pytest.raises(PathDoesntExistError):
        Config.load(Path("fake_path"))


def test_dump_config(mock_json_dump):
    config = Config(
        local_database_path="local_db_path",
        external_database_uri="external_db_uri",
        services=[],
    )
    fake_path = Path("fake_path")
    file_mock = MagicMock()

    with mock.patch.object(Config, "_create_if_not_exists") as create_mock, mock.patch.object(
        PosixPath, "open", new_callable=file_mock
    ) as open_mock:
        open_mock.return_value.__enter__.return_value = file_mock
        config.dump(fake_path)
    create_mock.assert_called_once_with(fake_path.expanduser().absolute())
    mock_json_dump.assert_called_once_with(config.model_dump(), file_mock)


def test_load_config(mock_json_load):
    fake_path = Path("fake_path")
    file_mock = MagicMock()
    with mock.patch("monitoring.config.check_path_existence"), mock.patch.object(
        PosixPath, "open", new_callable=file_mock
    ) as open_mock:
        open_mock.return_value.__enter__.return_value = file_mock
        Config.load(fake_path)
    mock_json_load.assert_called_once_with(file_mock)


@pytest.mark.parametrize("path_exists", (True, False))
def test_create_if_not_exists(path_exists):
    config = Config(
        local_database_path="local_db_path",
        external_database_uri="external_db_uri",
        services=[],
    )
    touch_mock = MagicMock()

    class PathMock(MagicMock):
        touch = touch_mock
        parent = None

        def exists(self):
            return path_exists

    path = PathMock("fake_path")
    with mock.patch("os.makedirs") as makedirs_mock:
        config._create_if_not_exists(path)

    if not path_exists:
        makedirs_mock.assert_called_once_with(path.parent, exist_ok=True)
        touch_mock.assert_called_once_with()
    else:
        makedirs_mock.assert_not_called()
        touch_mock.assert_not_called()


def test_sorted_services():
    service1 = HealthcheckConfig(url="http://url1", method=METHOD_GET, check_regex=False, regex="regex1")
    service2 = HealthcheckConfig(url="https://url2", method=METHOD_POST, check_regex=True, regex="regex2")
    service3 = HealthcheckConfig(url="http://url3", method=METHOD_OPTION, check_regex=False, regex="regex3")
    config = Config(
        local_database_path="",
        external_database_uri="",
        services=[service1, service2, service3],
    )
    assert config.sorted_services == [service1, service3, service2]


def test_databases_table():
    local_database_path = "local_db_path"
    external_database_uri = "external_db_uri"
    config = Config(
        local_database_path=local_database_path,
        external_database_uri=external_database_uri,
        services=[],
    )
    table = config.databases_table()
    assert local_database_path in table.get_string()
    assert external_database_uri in table.get_string()


def test_services_table():
    service1 = HealthcheckConfig(
        url="http://example.com/service1",
        method=METHOD_GET,
        check_regex=True,
        regex="/test1",
    )
    service2 = HealthcheckConfig(url="http://example.com/service2", method=METHOD_POST, check_regex=False)
    config = Config(
        local_database_path="local_db_path",
        external_database_uri="external_db_uri",
        services=[service1, service2],
    )

    table = config.services_table(numbered=True)
    expected_table = PrettyTable(
        field_names=[
            "№",
            "url",
            "method",
            "check_regex",
            "regex",
            "interval_sec",
            "timeout",
        ]
    )
    expected_table.add_row(
        [
            0,
            service1.url,
            service1.method,
            service1.check_regex,
            service1.regex,
            service1.interval_sec,
            service1.timeout,
        ]
    )
    expected_table.add_row(
        [
            1,
            service2.url,
            service2.method,
            service2.check_regex,
            service2.regex,
            service2.interval_sec,
            service2.timeout,
        ]
    )
    assert str(table) == str(expected_table)


def test_services_table_not_numbered():
    service1 = HealthcheckConfig(
        url="http://example.com/service1",
        method=METHOD_GET,
        check_regex=True,
        regex="/test1",
    )
    service2 = HealthcheckConfig(url="http://example.com/service2", method=METHOD_POST, check_regex=False)
    config = Config(
        local_database_path="local_db_path",
        external_database_uri="external_db_uri",
        services=[service1, service2],
    )
    table = config.services_table()

    expected_table = PrettyTable(field_names=["url", "method", "check_regex", "regex", "interval_sec", "timeout"])
    expected_table.add_row(
        [
            service1.url,
            service1.method,
            service1.check_regex,
            service1.regex,
            service1.interval_sec,
            service1.timeout,
        ]
    )
    expected_table.add_row(
        [
            service2.url,
            service2.method,
            service2.check_regex,
            service2.regex,
            service2.interval_sec,
            service2.timeout,
        ]
    )
    assert str(table) == str(expected_table)
