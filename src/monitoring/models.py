import datetime
import re
import uuid
from typing import Any, List, Optional, Tuple

from httpx import Response
from pydantic import BaseModel, model_validator

from monitoring.constants import (
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    HTTP_SCHEMA,
    HTTPS_SCHEMA,
    MAX_HEALTHCHECK_INTERVAL_SECONDS,
    MAX_URL_LENGTH,
    MIN_HEALTHCHECK_INTERVAL_SECONDS,
    SUPPORTED_METHODS,
)


class ServiceResponse(BaseModel):
    """Data model (representation) of a service response.

    Can be created from an exception, TimeoutError, ConnectionError, etc. or a normal HTTP response.
    """

    url: str
    method: str
    request_timestamp: datetime.datetime

    status_code: Optional[int] = None
    response_timestamp: Optional[datetime.datetime] = None

    regex_check_required: bool
    regex: Optional[str] = None
    contains_regex: bool = False

    contains_exception: bool = False
    exception: Optional[str] = None

    @staticmethod
    def _contains_regex(regex: str, text: Optional[str]) -> bool:
        """Check if string contains a specified regexp."""
        return text is not None and re.search(regex, text) is not None

    @classmethod
    def from_response(
        cls,
        url: str,
        response: Response,
        request_timestamp: datetime.datetime,
        response_timestamp: datetime.datetime,
        regex_check_required: bool,
        regex: Optional[str] = None,
    ) -> "ServiceResponse":
        """Build an object from a regular HTTP response."""
        klass = cls(
            url=url,
            method=response.request.method,
            status_code=response.status_code,
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            regex_check_required=regex_check_required,
            regex=regex,
        )
        if regex_check_required:
            if regex is None:
                raise ValueError("'regex' can't be None when regex check is required.")
            klass.contains_regex = cls._contains_regex(regex, response.text)
        return klass

    @classmethod
    def from_exception(
        cls,
        url: str,
        method: str,
        exception: Exception,
        request_timestamp: datetime.datetime,
        regex_check_required: bool,
        regex: Optional[str] = None,
    ) -> "ServiceResponse":
        """Build an object from an exception."""
        return cls(
            url=url,
            method=method,
            request_timestamp=request_timestamp,
            regex_check_required=regex_check_required,
            regex=regex,
            contains_exception=True,
            exception=str(exception),
        )


class ServiceResponseLocalDump(ServiceResponse):
    """Data model (representation) of the row that was inserted into the local database."""

    id: str
    created_at: datetime.datetime
    processed: bool = False

    @classmethod
    def from_service_response(cls, service_response: ServiceResponse) -> "ServiceResponseLocalDump":
        return cls(
            id=str(uuid.uuid4()),
            created_at=datetime.datetime.utcnow(),
            **service_response.model_dump(),
        )


class ServiceResponseRemoteDump(ServiceResponse):
    """Data model (representation) of the row that will be pushed to a remote database."""

    local_id: str
    local_created_at: datetime.datetime

    @classmethod
    def from_local_dump(cls, service_response: ServiceResponseLocalDump) -> "ServiceResponseRemoteDump":
        """Build a data model from a local row."""
        return cls(
            local_id=service_response.id,
            local_created_at=service_response.created_at,
            **service_response.model_dump(exclude={"id", "created_at"}),
        )

    def as_row(self) -> Tuple[Any, ...]:
        """Tuple data representation."""

        return (
            self.local_id,
            self.url,
            self.method,
            self.request_timestamp,
            self.regex_check_required,
            self.contains_regex,
            self.contains_exception,
            self.status_code,
            self.response_timestamp,
            self.regex,
            self.exception,
            self.local_created_at,
        )


class HealthcheckConfig(BaseModel):
    """Per-service configuration data model."""

    url: str
    method: str
    check_regex: bool
    regex: Optional[str] = None
    interval_sec: int = DEFAULT_REQUEST_INTERVAL_SECONDS
    timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS

    @model_validator(mode="after")
    def validate_url(self) -> "HealthcheckConfig":
        if len(self.url) > MAX_URL_LENGTH:
            raise ValueError("Invalid URL. Too long.")
        http = self.url.startswith(HTTP_SCHEMA)
        https = self.url.startswith(HTTPS_SCHEMA)
        if not https and not http:
            raise ValueError("Invalid HTTP schema.")
        return self

    @model_validator(mode="after")
    def validate_regex(self) -> "HealthcheckConfig":
        if self.check_regex and self.regex is None:
            raise ValueError("You must specify 'regex' when 'check_regex' is True.")
        return self

    @model_validator(mode="after")
    def validate_intervals(self) -> "HealthcheckConfig":
        if not (MIN_HEALTHCHECK_INTERVAL_SECONDS <= self.interval_sec <= MAX_HEALTHCHECK_INTERVAL_SECONDS):
            raise ValueError(
                f"Interval value must be between "
                f"{MIN_HEALTHCHECK_INTERVAL_SECONDS} and {MAX_HEALTHCHECK_INTERVAL_SECONDS}."
            )
        return self

    @model_validator(mode="after")
    def validate_method(self) -> "HealthcheckConfig":
        if self.method not in SUPPORTED_METHODS:
            raise ValueError(f"Method {self.method} is not supported. Available methods [ {SUPPORTED_METHODS} ].")
        return self

    @model_validator(mode="after")
    def validate_timeout(self) -> "HealthcheckConfig":
        if self.timeout <= 0:
            raise ValueError("Timeout must be greater than zero.")
        return self

    @property
    def sorting_helper(self) -> str:
        """Helper for returning services in a proper order."""
        return f"{self.url}{self.method}{self.check_regex}{self.regex}"

    @classmethod
    def fields(cls) -> List[str]:
        """Helper fields for data visualisation."""
        return [
            "url",
            "method",
            "check_regex",
            "regex",
            "interval_sec",
            "timeout",
        ]
