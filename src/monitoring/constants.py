"""Module with basic constants."""

METHOD_POST = "POST"
"""HTTP method POST."""
METHOD_GET = "GET"
"""HTTP method GET."""
METHOD_HEAD = "HEAD"
"""HTTP method HEAD."""
METHOD_OPTION = "OPTION"
"""HTTP method OPTION."""

SUPPORTED_METHODS = (
    METHOD_POST,
    METHOD_GET,
    METHOD_HEAD,
    METHOD_OPTION,
)
"""Currently supported HTTP methods."""

MAX_URL_LENGTH = 2083
"""Maximum length of a url."""

HTTP_SCHEMA = "http://"
"""HTTP schema URL prefix."""

HTTPS_SCHEMA = "https://"
"""HTTPS schema URL prefix."""

SUPPORTED_SCHEMAS = (
    HTTP_SCHEMA,
    HTTPS_SCHEMA,
)
"""Supported HTTP/S schemas (URL prefixes)."""

MIN_HEALTHCHECK_INTERVAL_SECONDS = 5
"""Minimal interval between HTTP requests."""
MAX_HEALTHCHECK_INTERVAL_SECONDS = 300
"""Maximum interval between HTTP requests."""

DEFAULT_REQUEST_INTERVAL_SECONDS = 5
"""Default interval between HTTP requests."""
DEFAULT_REQUEST_TIMEOUT_SECONDS = 15
"""Default timeout for a HTTP requests."""

DEFAULT_CONFIG_FILENAME = "monitoring-config"
"""Default filename of a tool configuration."""

DEFAULT_LOCALDB_FILENAME = "local-database.sqlite3"
"""Default filename of a local database."""

DEFAULT_CONFIG_PATH = f"~/.monitoring/{DEFAULT_CONFIG_FILENAME}"
"""Default path of a tool configuration."""
DEFAULT_LOCALDB_PATH = f"~/.monitoring/{DEFAULT_LOCALDB_FILENAME}"
"""Default path of a local database."""

DEFAULT_VERBOSITY_LEVEL = 0
"""Default logging level. Equivalent to logging.CRITICAL."""
DEBUG_LEVEL = 5
"""Default logging level. Equivalent to logging.DEBUG."""
INFO_LEVEL = 4
"""Default logging level. Equivalent to logging.INFO."""
WARNING_LEVEL = 3
"""Default logging level. Equivalent to logging.WARNING."""
ERROR_LEVEL = 2
"""Default logging level. Equivalent to logging.ERROR."""

LOGGING_VERBOSITY_LEVELS = (
    DEBUG_LEVEL,
    INFO_LEVEL,
    WARNING_LEVEL,
    ERROR_LEVEL,
)
"""Supported logging level."""

MINUTE_SECONDS = 60
"""Amount of minutes in a second."""

SYSTEMD_SOCKET = "/run/systemd/notify"
"""OS path to a systemd socket."""

SYSTEMD_NOTIFY_MESSAGE = b"READY=1"
"""Default systemd message."""

DEFAULT_HEADERS = {"user-agent": "monitoring-client"}
"""Default headers that will me attached to a HTTP request."""

DEFAULT_MAX_WORKERS = 1
"""Default max workers."""

MAX_RECONNECTION_ATTEMPTS = 15
"""Max reconnection attempts."""

MAX_SERVICES_PER_WORKER = 1000
"""Max services per worker."""

DEFAULT_BATCH_SIZE = 5000
"""Default export batch size."""

ALLOWED_TIME_ERROR_SECONDS = 0.2
"""Allowed error seconds."""
