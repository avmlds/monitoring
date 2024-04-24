from pathlib import Path

import pytest
from click.testing import CliRunner

from monitoring.constants import (
    DEFAULT_LOCALDB_PATH,
    HTTP_SCHEMA,
    HTTPS_SCHEMA,
    MAX_HEALTHCHECK_INTERVAL_SECONDS,
    MIN_HEALTHCHECK_INTERVAL_SECONDS,
    SUPPORTED_METHODS,
)
from monitoring.monitoring_cli import cli

runner = CliRunner()

EXIT_CODE_BAD_ARGUMENT = 2


def test_base_cli_invocation():
    response = runner.invoke(cli)
    assert response.exit_code == 0
    response = runner.invoke(cli, args=["config"])
    assert response.exit_code == 0
    response = runner.invoke(cli, args=["config", "databases"])
    assert response.exit_code == 0
    response = runner.invoke(cli, args=["config", "services"])
    assert response.exit_code == 0


@pytest.mark.parametrize("local_path", [None, "~/test-local-path"])
@pytest.mark.parametrize("config_path", ["~/test-config-path"])
def test_create_delete_config(local_path, config_path):
    create_args = ["config", "create", "postgresql://"]
    show_args = ["config", "show"]
    databases_show_args = ["config", "databases", "show"]
    delete_args = ["config", "delete"]

    if local_path:
        create_args.extend(["--local-path", local_path])
    if config_path:
        args = ["--config-path", config_path]
        create_args.extend(args)
        show_args.extend(args)
        databases_show_args.extend(args)
        delete_args.extend(args)

    create_response = runner.invoke(cli, args=create_args)
    assert create_response.exit_code == 0
    try:
        show_response = runner.invoke(cli, args=show_args)
        databases_show_response = runner.invoke(cli, args=databases_show_args)
        assert show_response.exit_code == 0
        assert databases_show_response.exit_code == 0
        if local_path:
            path = Path(local_path).expanduser().absolute().as_posix()
            assert path in show_response.stdout
            assert path in databases_show_response.stdout
        else:
            path = Path(DEFAULT_LOCALDB_PATH).expanduser().absolute().as_posix()
            assert path in show_response.stdout
            assert path in databases_show_response.stdout
    finally:
        delete_response = runner.invoke(cli, args=delete_args, input="y")
        assert delete_response.exit_code == 0
        if local_path:
            assert not Path(local_path).expanduser().absolute().exists()
        if config_path:
            assert not Path(config_path).expanduser().absolute().exists()


@pytest.mark.parametrize("config_path", ["~/test-config-path"])
@pytest.mark.parametrize("interval", [4, 5, 300, 301])
@pytest.mark.parametrize("timeout", [0, 10])
@pytest.mark.parametrize("regex", [None, "test"])
@pytest.mark.parametrize("check_regex", [True, False])
@pytest.mark.parametrize("method", [*SUPPORTED_METHODS, "PATCH"])
@pytest.mark.parametrize("url", ["http://test", "https://test", "ftp://test"])
def test_create_delete_services(  # noqa: PLR0912
    config_path,
    interval,
    timeout,
    regex,
    check_regex,
    method,
    url,
):
    all_args = [config_path, interval, timeout, regex, check_regex, method, url]
    create_args = ["config", "create", "postgresql://"]
    add_services_args = ["config", "services", "add"]
    remove_service_args = ["config", "services", "remove", "0"]
    show_services_args = ["config", "services", "show"]
    delete_args = ["config", "delete"]

    raises = False

    if config_path:
        config_args = ["--config-path", config_path]
        create_args.extend(config_args)
        add_services_args.extend(config_args)
        remove_service_args.extend(config_args)
        show_services_args.extend(config_args)
        delete_args.extend(config_args)

    if interval < MIN_HEALTHCHECK_INTERVAL_SECONDS or interval > MAX_HEALTHCHECK_INTERVAL_SECONDS:
        raises = True
    if timeout <= 0:
        raises = True
    if regex is None and check_regex:
        raises = True
    if method not in SUPPORTED_METHODS:
        raises = True
    if not url.startswith(HTTP_SCHEMA) or not url.startswith(HTTPS_SCHEMA):
        raises = True

    response = runner.invoke(cli, create_args)
    assert response.exit_code == 0
    try:
        add_service_response = runner.invoke(cli, add_services_args)
        show_services_response = runner.invoke(cli, show_services_args)

        if not raises:
            for arg in all_args:
                assert str(arg) in show_services_response.stdout
            assert add_service_response.exit_code == 0
            remove_service_response = runner.invoke(cli, remove_service_args)
            assert remove_service_response.exit_code == 0
            for arg in all_args:
                assert str(arg) not in remove_service_response.stdout
        else:
            for arg in all_args:
                assert str(arg) not in show_services_response.stdout
            assert add_service_response.exit_code == EXIT_CODE_BAD_ARGUMENT
    finally:
        delete_response = runner.invoke(cli, args=delete_args, input="y")
        assert delete_response.exit_code == 0


@pytest.mark.parametrize("config_path", ["~/test-config-path"])
@pytest.mark.parametrize("interval", [None, 4, 5, 300, 301])
@pytest.mark.parametrize("timeout", [None, 0, 10])
@pytest.mark.parametrize("regex", [None, "test"])
@pytest.mark.parametrize("toggle_check_regex", [True, False])
@pytest.mark.parametrize("create_with_regex", [True, False])
def test_update_services(  # noqa: PLR0912
    config_path,
    interval,
    timeout,
    regex,
    toggle_check_regex,
    create_with_regex,
):
    create_args = ["config", "create", "postgresql://"]
    delete_args = ["config", "delete"]
    create_service_args = [
        "config",
        "services",
        "add",
        "https://example.org/",
        "GET",
        "--timeout",
        "5",
        "--interval",
        "10",
    ]
    if create_with_regex:
        create_service_args.append("--check-regex")
        create_service_args.extend(["--regex", "test-regex"])

    update_service_args = [
        "config",
        "services",
        "update",
        "0",
    ]

    if interval is not None:
        update_service_args.extend(["--interval", interval])
    if timeout is not None:
        update_service_args.extend(["--timeout", timeout])
    if regex is not None:
        update_service_args.extend(["--regex", regex])
    if toggle_check_regex:
        update_service_args.append("--toggle-check-regex")

    if config_path:
        config_args = ["--config-path", config_path]
        create_args.extend(config_args)
        create_service_args.extend(config_args)
        update_service_args.extend(config_args)
        delete_args.extend(config_args)

    response = runner.invoke(cli, create_args)
    assert response.exit_code == 0
    try:
        create_service = runner.invoke(cli, create_service_args)
        assert create_service.exit_code == 0

        raises = False
        if interval is not None and (
            interval < MIN_HEALTHCHECK_INTERVAL_SECONDS or interval > MAX_HEALTHCHECK_INTERVAL_SECONDS
        ):
            raises = True
        if timeout is not None and timeout <= 0:
            raises = True
        if not create_with_regex:
            if toggle_check_regex and not regex:
                raises = True

        update_service = runner.invoke(cli, update_service_args, input="y")
        if raises:
            assert update_service.exit_code == EXIT_CODE_BAD_ARGUMENT
        else:
            assert update_service.exit_code == 0
            for arg in [interval, timeout, regex]:
                if arg is not None:
                    assert str(arg) in update_service.stdout
                if create_with_regex and toggle_check_regex:
                    assert str(False) in update_service.stdout
    finally:
        delete_response = runner.invoke(cli, args=delete_args, input="y")
        assert delete_response.exit_code == 0
