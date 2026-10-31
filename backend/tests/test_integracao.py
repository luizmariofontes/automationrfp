"""Testes com Postgres, Redis e worker Celery reais.

Rodam com `make test-integration` (serviços do docker compose no ar) ou no CI.
"""

import os

import pytest
from sqlalchemy import text

from app.shared.db import get_engine
from app.shared.tasks import ping

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="defina RUN_INTEGRATION=1"),
]


def test_readiness_com_servicos_reais(client):
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200, resp.json()
    assert resp.json()["checks"] == {"postgres": "ok", "redis": "ok"}


def test_extensoes_instaladas_pela_migracao():
    with get_engine().connect() as conn:
        exts = set(conn.execute(text("SELECT extname FROM pg_extension")).scalars())
    assert {"vector", "unaccent"} <= exts


@pytest.mark.skipif(os.getenv("CELERY_WORKER") != "1", reason="defina CELERY_WORKER=1")
def test_worker_consome_a_fila():
    assert ping.delay().get(timeout=20) == "pong"
