"""Rotas HTTP do módulo auditoria. Implementação prevista para o sprint 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])
