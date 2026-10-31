import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_JSON", "false")

from app.main import create_app
from app.shared.config import get_settings


@pytest.fixture
def app():
    return create_app(get_settings())


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
