"""Raiz de composição: cria a aplicação FastAPI, registra módulos, middleware e erros.

É o único lugar que conhece módulos e adaptadores concretos ao mesmo tempo.
"""

from importlib import import_module

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules import MODULES
from app.shared.config import Settings, get_settings
from app.shared.errors import register_error_handlers
from app.shared.health import router as health_router
from app.shared.logging import configure_logging
from app.shared.middleware import RequestContextMiddleware


def _module_routers() -> list[APIRouter]:
    routers: list[APIRouter] = []
    for name in MODULES:
        api = import_module(f"app.modules.{name}.api")
        routers.append(api.router)
    return routers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    app.include_router(health_router)
    for router in _module_routers():
        app.include_router(router)
    return app


app = create_app()
