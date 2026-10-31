"""Requisições.

Fluxo da requisição de RFI/RFP, estados, prazos e tarefas de validação por equipe.

Interface pública: `service.py` (chamado por outros módulos) e `api.py` (rotas HTTP).
Outros módulos NÃO importam `domain`, `repository` nem `models` deste pacote
(verificado em tests/test_arquitetura.py).
"""
