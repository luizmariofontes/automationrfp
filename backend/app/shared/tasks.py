"""Tarefas de infraestrutura. As tarefas de negócio ficam em `app/modules/<modulo>/tasks.py`."""

from app.shared.celery_app import celery_app
from app.shared.db import get_sessionmaker
from app.shared.eventos import despachar_pendentes


@celery_app.task(name="sistema.ping")
def ping() -> str:
    """Tarefa de exemplo usada para verificar se o worker está consumindo a fila."""
    return "pong"


@celery_app.task(name="sistema.despachar_outbox")
def despachar_outbox() -> int:
    """Entrega aos assinantes os eventos gravados na outbox."""
    with get_sessionmaker()() as db:
        return despachar_pendentes(db)
