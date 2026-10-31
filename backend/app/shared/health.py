"""Rotas de saúde: /health (processo vivo) e /api/v1/health/ready (dependências)."""

from collections.abc import Callable
from typing import Literal

import redis
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.shared.config import Settings, get_settings
from app.shared.db import ping_database

router = APIRouter(tags=["saúde"])

CheckStatus = Literal["ok", "falha"]


class Liveness(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    env: str


class Readiness(BaseModel):
    status: CheckStatus
    checks: dict[str, CheckStatus]


def ping_redis(settings: Settings) -> None:
    client = redis.Redis.from_url(
        settings.redis_url,
        socket_timeout=settings.readiness_timeout,
        socket_connect_timeout=settings.readiness_timeout,
    )
    try:
        client.ping()
    finally:
        client.close()


Checker = Callable[[Settings], None]


def get_checkers() -> dict[str, Checker]:
    """Dependência substituível nos testes."""
    return {
        "postgres": lambda s: ping_database(s.readiness_timeout),
        "redis": ping_redis,
    }


@router.get("/health", response_model=Liveness)
@router.get("/api/v1/health", response_model=Liveness, include_in_schema=False)
def liveness(settings: Settings = Depends(get_settings)) -> Liveness:  # noqa: B008
    return Liveness(app=settings.app_name, env=settings.app_env)


@router.get("/api/v1/health/ready", response_model=Readiness)
def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),  # noqa: B008
    checkers: dict[str, Checker] = Depends(get_checkers),  # noqa: B008
) -> Readiness:
    results: dict[str, CheckStatus] = {}
    for name, check in checkers.items():
        try:
            check(settings)
            results[name] = "ok"
        except Exception:  # qualquer falha de conexão conta como indisponível
            results[name] = "falha"
    overall: CheckStatus = "ok" if all(v == "ok" for v in results.values()) else "falha"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Readiness(status=overall, checks=results)
