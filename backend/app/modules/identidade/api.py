"""Rotas HTTP do módulo identidade e acesso. Implementação prevista para o sprint 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/identidade", tags=["identidade e acesso"])
