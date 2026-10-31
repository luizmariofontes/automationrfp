from app.shared.celery_app import celery_app
from app.shared.tasks import ping


def test_tarefa_ping_executa_em_modo_eager():
    celery_app.conf.task_always_eager = True
    try:
        assert ping.delay().get(timeout=1) == "pong"
    finally:
        celery_app.conf.task_always_eager = False


def test_rota_da_fila_de_cobranca():
    rotas = celery_app.conf.task_routes
    assert rotas["cobranca.*"] == {"queue": "cobranca"}
