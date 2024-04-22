from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest

from monitoring.config import Config
from monitoring.constants import METHOD_GET
from monitoring.models import HealthcheckConfig, ServiceResponse
from monitoring.workers import Agent

URL = "http://example.com"


def test_estimate_workload():
    config = Config(
        local_database_path="",
        external_database_uri="",
        services=[
            HealthcheckConfig(
                method=METHOD_GET,
                url=URL,
                check_regex=False,
                interval_sec=60,
                timeout=10,
            ),
            HealthcheckConfig(
                method=METHOD_GET,
                url=URL,
                check_regex=True,
                regex="pattern",
                interval_sec=30,
                timeout=5,
            ),
        ],
    )

    agent = Agent(config=config, database_manager=MagicMock())
    assert agent.estimate_workload() == (3.0, 1.5)


async def dummy_run_in_executor(executor, func, *args):
    return func(*args)


@pytest.mark.asyncio
async def test_task():
    config = HealthcheckConfig(
        method=METHOD_GET,
        url=URL,
        check_regex=False,
        interval_sec=60,
        timeout=10,
    )
    service_response = ServiceResponse(
        url=URL,
        method=METHOD_GET,
        request_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
        contains_regex=True,
    )

    database_manager = MagicMock()
    database_manager.dump = MagicMock()
    agent = Agent(config=MagicMock(), database_manager=database_manager)
    with mock.patch("asyncio.get_running_loop") as mock_get_running_loop, mock.patch(
        "asyncio.sleep"
    ) as sleep_mock, mock.patch(
        "monitoring.workers.monitoring.send_async_request",
        return_value=service_response,
    ) as send_request_mock:
        mock_get_running_loop.return_value.run_in_executor = MagicMock(side_effect=dummy_run_in_executor)
        await agent._task(config)
        send_request_mock.assert_called_once_with(
            config.method,
            config.url,
            regex_check_required=config.check_regex,
            regex=config.regex,
            timeout=config.timeout,
        )
        mock_get_running_loop.return_value.run_in_executor.assert_called_once_with(
            None, agent.database_manager.dump, service_response
        )
        sleep_mock.assert_called_once_with(config.interval_sec)
