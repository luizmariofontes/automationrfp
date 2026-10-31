"""Middleware de request id e log de acesso (sem corpo da requisição)."""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger("http")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

        response.headers[REQUEST_ID_HEADER] = request_id
        log.info(
            "requisicao",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=elapsed_ms,
        )
        return response
