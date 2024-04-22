from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from monitoring.constants import METHOD_GET
from monitoring.database import LocalDatabaseManager
from monitoring.models import ServiceResponse
from monitoring.queries import (
    COUNT_PROCESSED,
    CREATE_LOCAL_MONITORING_TABLE,
    DELETE_PROCESSED,
    SELECT_UNPROCESSED,
)

URL = "http://example.com"
FAKE_PATH = Path("test.db")


def test_init(mock_connection):
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    manager.init()
    mock_connection.execute.assert_called_once_with(CREATE_LOCAL_MONITORING_TABLE)
    mock_connection.commit.assert_called_once()


def test_dump(mock_connection):
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    manager._LOCK = MagicMock()
    service_response = ServiceResponse(
        url=URL,
        method=METHOD_GET,
        request_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
        contains_regex=True,
    )
    manager.dump(service_response)
    manager._LOCK.__enter__.assert_called_once()
    mock_connection.execute.assert_called_once()
    mock_connection.commit.assert_called_once()


def test_load_unprocessed(mock_connection):
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    rows = manager.load_unprocessed()
    mock_connection.execute.assert_called_once_with(SELECT_UNPROCESSED)
    assert len(rows) == 0


def test_mark_as_processed(mock_connection):
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    manager._LOCK = MagicMock()
    manager.mark_as_processed(["a", "b", "c"])
    manager._LOCK.__enter__.assert_called_once()
    mock_connection.execute.assert_called_once()
    mock_connection.commit.assert_called_once()


def test_delete_processed(mock_connection):
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    manager._LOCK = MagicMock()
    manager.delete_processed()
    manager._LOCK.__enter__.assert_called_once()
    mock_connection.execute.assert_called_once_with(DELETE_PROCESSED)
    mock_connection.commit.assert_called_once()


def test_count_processed(mock_connection):
    row_count = 10
    cursor = MagicMock()
    cursor.fetchone.return_value = (row_count,)
    mock_connection.execute.return_value = cursor
    manager = LocalDatabaseManager(path=FAKE_PATH, connection=mock_connection)
    count = manager.count_processed()
    mock_connection.execute.assert_called_once_with(COUNT_PROCESSED)
    assert count == row_count
