"""Rotas HTTP do módulo base de conhecimento. Implementação prevista para o sprint 3."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/conhecimento", tags=["base de conhecimento"])
