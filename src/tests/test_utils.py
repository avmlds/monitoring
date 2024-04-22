import httpx
import pytest
from httpx import Request, Response

from monitoring.constants import METHOD_GET
from monitoring.exceptions import InvalidParameterValueError, UnsupportedMethodError
from monitoring.models import ServiceResponse
from monitoring.utils import send_async_request

URL = "http://example.com"


@pytest.mark.asyncio
async def test_send_async_request_valid():
    async def mock_request(*args, **kwargs):
        return httpx.Response(200, content="Test Response")

    with pytest.raises(UnsupportedMethodError):
        async with httpx.AsyncClient() as client:
            client.request = mock_request
            await send_async_request(
                "PATCH",
                URL,
                regex_check_required=False,
                timeout=5,
            )


@pytest.mark.asyncio
async def test_send_async_request_invalid_timeout():
    with pytest.raises(InvalidParameterValueError):
        await send_async_request(METHOD_GET, URL, regex_check_required=False, timeout=-1)


@pytest.mark.asyncio
async def test_send_async_request_from_response(mock_httpx_client_response):
    HTTP_CODE_TEAPOT = 418
    mock_httpx_client_response.return_value = Response(
        request=Request(METHOD_GET, URL), status_code=HTTP_CODE_TEAPOT, text="I'm a teapot"
    )

    service_response = await send_async_request(METHOD_GET, URL, regex_check_required=True, regex="tea")
    assert isinstance(service_response, ServiceResponse)
    assert service_response.url == URL
    assert service_response.method == METHOD_GET
    assert service_response.status_code == HTTP_CODE_TEAPOT
    assert not service_response.contains_exception
    assert service_response.contains_regex


@pytest.mark.asyncio
async def test_send_async_request_from_exception(mock_httpx_client_response):
    message = "unforeseen consequences"

    def unforeseen_consequences(*args, **kwargs):
        raise Exception(message)

    mock_httpx_client_response.side_effect = unforeseen_consequences
    service_response = await send_async_request(METHOD_GET, URL, regex_check_required=False)

    assert isinstance(service_response, ServiceResponse)
    assert service_response.contains_exception
    assert service_response.exception == message
