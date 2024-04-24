"""Module with exceptions."""


class UnsupportedMethodError(Exception):
    """Unsupported HTTP method error."""

    def __init__(self, method: str) -> None:
        super().__init__(f"Method {method} is not supported.")


class InvalidParameterValueError(Exception):
    """Invalid parameter value."""

    def __init__(self, parameter: str) -> None:
        super().__init__(
            f"Parameter '{parameter}' value can't be less or equal to zero",
        )


class PathDoesntExistError(Exception):
    """Raised when a specified path doesn't exist on a filesystem."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Specified path '{path}' does not exist.")


class NoServicesSpecifiedError(Exception):
    """Raised when configuration file contains no services."""

    def __init__(self) -> None:
        super().__init__("Config doesn't contain any services. Add service first.")


class InvalidConfigurationFileError(Exception):
    """Raised when configuration file has an invalid format."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Specified configuration file '{path}' is not valid or corrupted.")
