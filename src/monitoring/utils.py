import datetime
import logging
from pathlib import Path

import aiohttp

from monitoring.constants import (
    DEFAULT_HEADERS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    SUPPORTED_METHODS,
)
from monitoring.exceptions import (
    InvalidParameterValueError,
    PathDoesntExistError,
    UnsupportedMethodError,
)
from monitoring.models import ServiceResponse

LOG = logging.getLogger()


async def send_async_request(
    method: str,
    url: str,
    *,
    regex_check_required: bool,
    timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    regex: None | str = None,
) -> ServiceResponse:
    """Send an HTTP request to a specified URL."""
    if method not in SUPPORTED_METHODS:
        raise UnsupportedMethodError(method)

    if timeout < 0:
        raise InvalidParameterValueError("timeout")

    request_timestamp = datetime.datetime.now(datetime.UTC)
    try:
        async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as client:
            async with client.request(method, url, timeout=timeout) as response:
                response_timestamp = datetime.datetime.now(datetime.UTC)
                LOG.info(f"Success | {response.status} | '{method}' | '{url}'")
                response_text = await response.text()
                return ServiceResponse.from_response(
                    url=url,
                    method=method,
                    status=response.status,
                    response_text=response_text,
                    request_timestamp=request_timestamp,
                    response_timestamp=response_timestamp,
                    regex_check_required=regex_check_required,
                    regex=regex,
                )
    except (ConnectionError, Exception) as e:
        LOG.error(f"Failure | XXX | '{method}' | '{url}' | '{e}'")
        return ServiceResponse.from_exception(
            url,
            method,
            e,
            request_timestamp,
            regex_check_required,
            regex,
        )


def check_path_existence(path: Path) -> None:
    if not path.exists():
        raise PathDoesntExistError(path.as_posix())
