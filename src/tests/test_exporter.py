import asyncio
import socket
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from monitoring.config import Config
from monitoring.constants import METHOD_GET
from monitoring.models import ServiceResponseLocalDump
from monitoring.queries import INSERT_REMOTE_MONITORING_TABLE
from monitoring.workers import Exporter


async def dummy_executemany(*args, **kwargs):
    pass


async def dummy_fetch(*args, **kwargs):
    return [{"local_id": "1"}, {"local_id": "2"}]


def test_prepare_select_inserted_query():
    # Test prepare_select_inserted_query method
    rows_to_insert = [("1",), ("2",)]
    expected_query = "SELECT local_id FROM monitoring WHERE local_id IN ($1, $2);"
    assert Exporter.prepare_select_inserted_query(rows_to_insert) == expected_query


@pytest.mark.asyncio
async def test_export_rows():
    rows = [
        ServiceResponseLocalDump(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            url="http://localhost",
            method=METHOD_GET,
            request_timestamp=datetime.now(),
            regex_check_required=False,
            regex=None,
            contains_regex=False,
            contains_exception=False,
            status_code=200,
            response_timestamp=datetime.now(),
            exception=None,
        )
    ]
    rows_to_export = [
        (
            rows[0].id,
            rows[0].url,
            rows[0].method,
            rows[0].request_timestamp,
            rows[0].regex_check_required,
            rows[0].contains_regex,
            rows[0].contains_exception,
            rows[0].status_code,
            rows[0].response_timestamp,
            rows[0].regex,
            rows[0].exception,
            rows[0].created_at,
        )
    ]

    mock_pool = MagicMock()
    mock_pool.executemany = AsyncMock(side_effect=dummy_executemany)
    mock_pool.fetch = AsyncMock(side_effect=dummy_fetch)

    mock_pool.acquire.return_value.__aenter__.return_value = mock_pool

    exporter = Exporter(MagicMock(), MagicMock())
    exporter.get_pool = AsyncMock(return_value=mock_pool)
    exporter.database_manager.mark_as_processed = MagicMock()

    await exporter._export_rows(rows)

    exporter.get_pool.assert_called_once()
    mock_pool.executemany.assert_called_once_with(INSERT_REMOTE_MONITORING_TABLE, rows_to_export)
    mock_pool.fetch.assert_called_once()
    exporter.database_manager.mark_as_processed.assert_called_once_with(["1", "2"])


@pytest.mark.asyncio
async def test_task():
    rows = [
        ServiceResponseLocalDump(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            url="http://localhost",
            method=METHOD_GET,
            request_timestamp=datetime.now(),
            regex_check_required=False,
            regex=None,
            contains_regex=False,
            contains_exception=False,
            status_code=200,
            response_timestamp=datetime.now(),
            exception=None,
        )
    ]

    asyncio.sleep = AsyncMock()
    exporter = Exporter(MagicMock(), MagicMock())
    exporter._export_rows = AsyncMock()
    exporter.database_manager.load_unprocessed = MagicMock(return_value=rows)

    await exporter._task()

    exporter.database_manager.load_unprocessed.assert_called_once()
    exporter._export_rows.assert_called_once_with(rows)
    asyncio.sleep.assert_called_once_with(Exporter.SLEEP_TIME_SECONDS)


@pytest.mark.asyncio
async def test_task_negative():
    rows = []

    asyncio.sleep = AsyncMock()

    exporter = Exporter(MagicMock(), MagicMock())

    exporter._export_rows = AsyncMock()
    exporter.database_manager.load_unprocessed = MagicMock(return_value=rows)

    await exporter._task()

    exporter.database_manager.load_unprocessed.assert_called_once()
    exporter._export_rows.assert_not_called()
    asyncio.sleep.assert_called_once_with(Exporter.SLEEP_TIME_SECONDS)


@pytest.mark.parametrize(
    "exception", (ConnectionRefusedError, ConnectionError, ConnectionResetError, ConnectionAbortedError, socket.gaierror)
)
@pytest.mark.asyncio
async def test_task_connection_lost(exception):
    rows = [
        ServiceResponseLocalDump(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            url="http://localhost",
            method=METHOD_GET,
            request_timestamp=datetime.now(),
            regex_check_required=False,
            regex=None,
            contains_regex=False,
            contains_exception=False,
            status_code=200,
            response_timestamp=datetime.now(),
            exception=None,
        )
    ]

    asyncio.sleep = AsyncMock()

    async def panic(*args, **kwargs):
        raise exception

    exporter = Exporter(MagicMock(), MagicMock())
    exporter.pool = MagicMock()
    exporter.pool.terminate = MagicMock()
    exporter._export_rows = AsyncMock(side_effect=panic)
    exporter.database_manager.load_unprocessed = MagicMock(return_value=rows)

    await exporter._task()

    exporter.database_manager.load_unprocessed.assert_called_once()
    assert exporter.pool is None
    asyncio.sleep.assert_called_once_with(Exporter.SLEEP_TIME_SECONDS)


@pytest.mark.asyncio
async def test_get_pool():
    config = Config(
        local_database_path="local",
        external_database_uri="external",
        services=[],
    )
    exporter = Exporter(config, MagicMock())
    exporter._get_pool = AsyncMock()
    await exporter.get_pool()
    exporter._get_pool.assert_called_once_with(config.external_database_uri)
    exporter._get_pool.reset_mock()
    await exporter.get_pool()
    exporter._get_pool.assert_not_called()
