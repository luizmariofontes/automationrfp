"""Serviço público do módulo motor de respostas (o agente).

Funções deste arquivo são a única porta de entrada para outros módulos.

Regras de isolamento do agente (ver "O que o agente vê" no README):
- de uma requisição, este módulo só aceita `VisaoAgente` (app/shared/agente.py);
- não importa `cadastros`, `requisicoes`, `comunicacao` nem `privacidade` (import-linter);
- lê o banco pelo papel restrito ao schema `agente` (`get_agente_sessionmaker`);
- chama o modelo só pelo `LLMGateway`.

A geração de respostas entra no sprint 7.
"""

from app.shared.agente import ModeloImplantacao, VisaoAgente

__all__ = ["ModeloImplantacao", "VisaoAgente"]
