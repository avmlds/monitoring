from monitoring.config import Config
from monitoring.constants import METHOD_GET
from monitoring.execution import estimate_workload
from monitoring.models import HealthcheckConfig
from tests.test_models import URL


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
    assert estimate_workload(config) == (0.05, 0.025)
