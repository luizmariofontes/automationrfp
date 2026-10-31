"""Rotas HTTP do módulo questionários. Implementação prevista para o sprint 4."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/questionarios", tags=["questionários"])
