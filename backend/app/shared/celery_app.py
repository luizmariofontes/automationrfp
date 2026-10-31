"""Aplicação Celery compartilhada.

Filas:
- `default`: ingestão de documentos, geração em lote, e-mails do chat, expurgo
- `cobranca`: worker de cobrança (processo separado, ver ADR-006)
"""

from celery import Celery

from app.shared.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rfp_automation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.shared.tasks"],
)

celery_app.conf.update(
    task_default_queue="default",
    task_routes={"cobranca.*": {"queue": "cobranca"}},
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    result_expires=3600,
    # O agendamento (Celery Beat) é preenchido pelo módulo de cobrança no Sprint 9.
    beat_schedule={},
)
