"""Motor de respostas.

Geração de respostas (biblioteca, depois RAG), confiança e roteamento de equipes.

Interface pública: `service.py` (chamado por outros módulos) e `api.py` (rotas HTTP).
Outros módulos NÃO importam `domain`, `repository` nem `models` deste pacote
(verificado em tests/test_arquitetura.py).
"""
