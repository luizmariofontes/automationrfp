"""Rotas HTTP do módulo biblioteca de respostas. Implementação prevista para o sprint 8."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/biblioteca", tags=["biblioteca de respostas"])
