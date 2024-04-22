import uuid
from datetime import datetime

import pytest
from httpx import Request, Response

from monitoring.constants import MAX_URL_LENGTH, METHOD_GET, METHOD_POST
from monitoring.models import (
    HealthcheckConfig,
    ServiceResponse,
    ServiceResponseLocalDump,
    ServiceResponseRemoteDump,
)

URL = "http://example.com"
HTTP_CODE_200 = 200


def test_service_response_from_response():
    get_request = Request(method=METHOD_GET, url=URL)
    fake_response = Response(status_code=HTTP_CODE_200, text="Test Response", request=get_request)
    service_response = ServiceResponse.from_response(
        url=URL,
        response=fake_response,
        request_timestamp=datetime.now(),
        response_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
    )

    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.status_code == HTTP_CODE_200
    assert service_response.contains_regex is True


def test_service_response_from_response_negative():
    get_request = Request(method=METHOD_GET, url=URL)
    fake_response = Response(status_code=HTTP_CODE_200, text="Test Response", request=get_request)
    with pytest.raises(ValueError):
        ServiceResponse.from_response(
            url=URL,
            response=fake_response,
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
    )

    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.contains_exception is True
    assert service_response.exception == str(exception)


def test_service_response_local_dump_from_service_response():
    service_response = ServiceResponse(
        url=URL,
        method=METHOD_GET,
        request_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
        contains_regex=True,
    )
    local_dump = ServiceResponseLocalDump.from_service_response(service_response)
    assert hasattr(local_dump, "id")
    assert hasattr(local_dump, "created_at")
    assert local_dump.url == URL
    assert local_dump.method == METHOD_GET
    assert local_dump.contains_regex is True
    assert local_dump.processed is False


def test_service_response_remote_dump_from_local_dump():
    uid = str(uuid.uuid4())
    local_created_at = datetime.now()
    local_dump = ServiceResponseLocalDump(
        id=uid,
        created_at=local_created_at,
        url=URL,
        method=METHOD_GET,
        request_timestamp=datetime.now(),
        regex_check_required=True,
        regex=r".*Test.*",
        contains_regex=True,
        contains_exception=False,
        status_code=HTTP_CODE_200,
        response_timestamp=datetime.now(),
        exception=None,
    )

    remote_dump = ServiceResponseRemoteDump.from_local_dump(local_dump)
    assert remote_dump.local_id == uid
    assert remote_dump.local_created_at == local_created_at
    assert remote_dump.url == URL
    assert remote_dump.method == METHOD_GET
    assert remote_dump.contains_regex is True


def test_service_response_remote_dump_as_row():
    remote_dump = ServiceResponseRemoteDump(
        local_id=str(uuid.uuid4()),
        local_created_at=datetime.now(),
        url=URL,
        method=METHOD_POST,
        request_timestamp=datetime.now(),
        regex_check_required=False,
        regex=r".*Test.*",
        contains_regex=False,
        contains_exception=False,
        status_code=404,
        response_timestamp=datetime.now(),
        exception=None,
    )

    row = remote_dump.as_row()

    assert isinstance(row, tuple)
    assert row == (
        remote_dump.local_id,
        remote_dump.url,
        remote_dump.method,
        remote_dump.request_timestamp,
        remote_dump.regex_check_required,
        remote_dump.contains_regex,
        remote_dump.contains_exception,
        remote_dump.status_code,
        remote_dump.response_timestamp,
        remote_dump.regex,
        remote_dump.exception,
        remote_dump.local_created_at,
    )


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
