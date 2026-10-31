"""Rotas HTTP do módulo requisições. Implementação prevista para o sprint 6."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/requisicoes", tags=["requisições"])
