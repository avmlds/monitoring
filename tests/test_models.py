from datetime import datetime

import pytest

from monitoring.constants import MAX_URL_LENGTH, METHOD_GET
from monitoring.models import (
    HealthcheckConfig,
    ServiceResponse,
)

URL = "http://example.com"
HTTP_CODE_200 = 200


def test_service_response_from_response():
    service_response = ServiceResponse.from_response(
        url=URL,
        method=METHOD_GET,
        status=HTTP_CODE_200,
        response_text="Test Response",
        request_timestamp=datetime.now(),
        response_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
    )

    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.status_code == HTTP_CODE_200
    assert service_response.contains_regex is True


def test_service_response_empty_response_text():
    service_response = ServiceResponse.from_response(
        url=URL,
        method=METHOD_GET,
        status=HTTP_CODE_200,
        response_text=None,
        request_timestamp=datetime.now(),
        response_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
    )

    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.status_code == HTTP_CODE_200
    assert service_response.contains_regex is False


def test_service_response_from_response_negative():
    with pytest.raises(ValueError):
        ServiceResponse.from_response(
            url=URL,
            method=METHOD_GET,
            status=HTTP_CODE_200,
            response_text="Test Response",
            request_timestamp=datetime.now(),
            response_timestamp=datetime.now(),
            regex_check_required=True,
            regex=None,
        )


def test_service_response_from_exception():
    exception = Exception("Test Exception")
    service_response = ServiceResponse.from_exception(
        url=URL,
        method=METHOD_GET,
        exception=exception,
        request_timestamp=datetime.now(),
        regex_check_required=False,
        response_timestamp=datetime.now(),
    )

    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.contains_exception is True
    assert service_response.exception == str(exception)


def test_validate_url_valid():
    config = HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False)
    assert URL == config.url


def test_validate_url_invalid_length():
    with pytest.raises(ValueError):
        HealthcheckConfig(
            url="https://" + "a" * (MAX_URL_LENGTH + 1),
            method=METHOD_GET,
            check_regex=False,
        )


def test_validate_url_invalid_schema():
    with pytest.raises(ValueError):
        HealthcheckConfig(url="ftp://example.com", method=METHOD_GET, check_regex=False)


def test_validate_regex_valid():
    HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=True, regex="test")


def test_validate_regex_invalid():
    with pytest.raises(ValueError):
        HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=True)


def test_validate_intervals_valid():
    HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False, interval_sec=60)


def test_validate_intervals_invalid():
    with pytest.raises(ValueError):
        HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False, interval_sec=301)


def test_validate_method_invalid():
    with pytest.raises(ValueError):
        HealthcheckConfig(url=URL, method="PATCH", check_regex=False)


def test_validate_timeout_valid():
    HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False, timeout=5)


def test_validate_timeout_invalid():
    with pytest.raises(ValueError):
        HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False, timeout=0)


def test_sorting_helper():
    config = HealthcheckConfig(url=URL, method=METHOD_GET, check_regex=False)
    assert config.sorting_helper == f"{config.url}{config.method}{config.check_regex}{config.regex}"
