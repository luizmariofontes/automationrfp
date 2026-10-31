"""Biblioteca de respostas.

Respostas aprovadas e anonimizadas, reaproveitadas em novas requisições.

Interface pública: `service.py` (chamado por outros módulos) e `api.py` (rotas HTTP).
Outros módulos NÃO importam `domain`, `repository` nem `models` deste pacote
(verificado em tests/test_arquitetura.py).
"""
