"""Rotas HTTP do módulo cobrança. Implementação prevista para o sprint 9."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/cobranca", tags=["cobrança"])
