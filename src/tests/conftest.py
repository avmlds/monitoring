import sqlite3
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture
def mock_socket():
    with patch("socket.socket") as mock_socket:
        yield mock_socket


def json_load_mock(f):
    return {
        "local_database_path": "local_db_path",
        "external_database_uri": "external_db_uri",
        "services": [],
    }


def json_dump(obj, f):
    pass


@pytest.fixture
def mock_json_load():
    with patch("json.load", side_effect=json_load_mock) as mock_json:
        yield mock_json


@pytest.fixture
def mock_json_dump():
    with patch("json.dump", side_effect=json_dump) as mock_json:
        yield mock_json


@pytest.fixture()
def mock_httpx_client_response():
    with patch.object(httpx.AsyncClient, "request") as mock_response:
        yield mock_response


@pytest.fixture
def mock_connection():
    connection = MagicMock(spec=sqlite3.Connection)
    connection.execute = MagicMock()
    connection.commit = MagicMock()
    return connection
