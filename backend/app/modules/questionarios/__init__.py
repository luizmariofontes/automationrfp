"""Questionários.

Modelo canônico de perguntas e adaptadores de canal (Excel, web).

Interface pública: `service.py` (chamado por outros módulos) e `api.py` (rotas HTTP).
Outros módulos NÃO importam `domain`, `repository` nem `models` deste pacote
(verificado em tests/test_arquitetura.py).
"""
