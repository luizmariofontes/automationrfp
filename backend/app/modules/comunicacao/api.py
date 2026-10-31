"""Rotas HTTP do módulo comunicação. Implementação prevista para o sprint 10."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/comunicacao", tags=["comunicação"])
