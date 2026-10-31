"""Tarefas de infraestrutura. As tarefas de negócio ficam em `app/modules/<modulo>/tasks.py`."""

from app.shared.celery_app import celery_app


@celery_app.task(name="sistema.ping")
def ping() -> str:
    """Tarefa de exemplo usada para verificar se o worker está consumindo a fila."""
    return "pong"
