"""Erros de aplicação e formato padrão de resposta de erro.

Toda resposta de erro da API segue o formato:

    {"error": {"code": "...", "message": "...", "request_id": "...", "details": ...}}
"""

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)


class AppError(Exception):
    """Erro de negócio esperado. Os módulos lançam subclasses deste erro."""

    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "erro_aplicacao"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "nao_encontrado"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflito"


class ForbiddenError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "acesso_negado"


def _body(code: str, message: str, request: Request, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, request, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Não devolvemos o valor recebido ("input"), que pode conter dados de clientes.
        details = [
            {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content=_body("validacao", "Dados inválidos.", request, details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "nao_encontrado", 405: "metodo_nao_permitido", 401: "nao_autenticado"}.get(
            exc.status_code, "erro_http"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(code, str(exc.detail), request),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.error("erro_inesperado", exc_type=type(exc).__name__, path=request.url.path)
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=_body(
                "erro_interno", "Erro interno. Informe o request_id ao suporte.", request
            ),
        )
