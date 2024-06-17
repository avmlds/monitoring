import datetime
import re
from typing import List

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

    status_code: None | int = None
    response_timestamp: None | datetime.datetime = None

    regex_check_required: bool
    regex: None | str = None
    contains_regex: bool = False

    contains_exception: bool = False
    exception: None | str = None

    @staticmethod
    def _contains_regex(regex: str, text: None | str) -> bool:
        """Check if string contains a specified regexp."""
        return text is not None and re.search(regex, text) is not None

    @classmethod
    def from_response(
        cls,
        url: str,
        method: str,
        status: int,
        response_text: None | str,
        request_timestamp: datetime.datetime,
        response_timestamp: datetime.datetime,
        regex_check_required: bool,
        regex: None | str = None,
    ) -> "ServiceResponse":
        """Build an object from a regular HTTP response."""
        klass = cls(
            url=url,
            method=method,
            status_code=status,
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            regex_check_required=regex_check_required,
            regex=regex,
        )
        if regex_check_required:
            if regex is None:
                raise ValueError("'regex' can't be None when regex check is required.")
            klass.contains_regex = cls._contains_regex(regex, response_text)
        return klass

    @classmethod
    def from_exception(
        cls,
        url: str,
        method: str,
        exception: Exception,
        request_timestamp: datetime.datetime,
        response_timestamp: datetime.datetime,
        regex_check_required: bool,
        regex: None | str = None,
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
            response_timestamp=response_timestamp,
        )


class HealthcheckConfig(BaseModel):
    """Per-service configuration data model."""

    _MAXIMUM_PRIORITY = 0.0

    url: str
    method: str
    check_regex: bool
    last_checked_at: None | datetime.datetime = None
    regex: None | str = None
    interval_sec: int = DEFAULT_REQUEST_INTERVAL_SECONDS
    timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS

    def __lt__(self, other: "HealthcheckConfig") -> bool:
        return self.priority_seconds < other.priority_seconds

    @property
    def priority_seconds(self) -> float:
        if self.last_checked_at is None:
            return self._MAXIMUM_PRIORITY
        return self.interval_sec - (datetime.datetime.now(datetime.UTC) - self.last_checked_at).total_seconds()

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
