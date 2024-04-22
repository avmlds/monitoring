from unittest.mock import MagicMock, patch

import pytest

from monitoring.workers import Collector


async def dummy_run_in_executor(executor, func, *args):
    return func(*args)


@pytest.mark.asyncio
async def test_collector_task():
    mock_count_processed = MagicMock(return_value=10)
    mock_delete_processed = MagicMock()
    collector = Collector(MagicMock(), MagicMock())
    collector.database_manager.count_processed = mock_count_processed
    collector.database_manager.delete_processed = mock_delete_processed
    with patch("asyncio.get_running_loop") as mock_get_running_loop, patch("asyncio.sleep"):
        mock_get_running_loop.return_value.run_in_executor = MagicMock(side_effect=dummy_run_in_executor)
        await collector._task()
    mock_count_processed.assert_called_once()
    mock_delete_processed.assert_called_once()
