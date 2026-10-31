"""Base de conhecimento.

Ingestão de documentos, trechos, embeddings e busca híbrida.

Interface pública: `service.py` (chamado por outros módulos) e `api.py` (rotas HTTP).
Outros módulos NÃO importam `domain`, `repository` nem `models` deste pacote
(verificado em tests/test_arquitetura.py).
"""
