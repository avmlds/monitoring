import datetime
import logging
from pathlib import Path
from typing import Optional

import httpx

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
    regex: Optional[str] = None,
) -> ServiceResponse:
    if method not in SUPPORTED_METHODS:
        raise UnsupportedMethodError(method)

    if timeout < 0:
        raise InvalidParameterValueError("timeout")

    async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS) as client:
        request_timestamp = datetime.datetime.utcnow()
        try:
            response = await client.request(method, url)
            response_timestamp = datetime.datetime.utcnow()
            LOG.info(f"Success | {response.status_code} | '{method}' | '{url}'")
            return ServiceResponse.from_response(
                url,
                response,
                request_timestamp,
                response_timestamp,
                regex_check_required,
                regex,
            )
        except Exception as e:
            LOG.info(f"Failure | XXX | '{method}' | '{url}' | '{e}'")
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
