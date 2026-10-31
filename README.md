# RFP Automation

Automação de preenchimento de RFPs e RFIs com IA. Responde questionários em Excel ou web a partir de uma base de documentos (RAG) e de uma biblioteca de respostas aprovadas, distribui validações por equipe com cobrança de prazos, oferece um chat por requisição espelhado por e-mail e expurga o arquivo original ao concluir.

Arquitetura e plano: documento "Plano de Implementação do Piloto — Automação RFP/RFI" (abas *Arquitetura* e *Plano de execução*).

## Estado atual

**Sprint 1 — Esqueleto (concluído).** Estrutura de módulos, API com saúde e erros padronizados, logs JSON, banco com migrações, Celery, Docker Compose, CI e front-end base.

## Como rodar

Pré-requisitos (no Windows, dentro do WSL2 com Ubuntu 24.04): Docker, `make`, Git. Para rodar fora do Docker: Python 3.12 com [uv](https://docs.astral.sh/uv/) e Node 22 com pnpm.

```bash
make up        # cria o .env e sobe api, workers, front, postgres, redis, minio e mailpit
make migrate   # aplica as migrações
make test      # testes do backend
make lint      # ruff, mypy, import-linter e lint do front
make help      # todos os comandos
```

| Serviço | Endereço |
| --- | --- |
| Interface | http://localhost:5173 |
| API (documentação OpenAPI) | http://localhost:8000/api/docs |
| Saúde das dependências | http://localhost:8000/api/v1/health/ready |
| Console do MinIO | http://localhost:9001 |
| E-mails capturados (Mailpit) | http://localhost:8025 |

### Sem Docker

```bash
cd backend
uv sync
uv run alembic upgrade head          # precisa de Postgres com pgvector e Redis
uv run uvicorn app.main:app --reload
uv run celery -A app.shared.celery_app worker -Q default,cobranca -l info

cd ../frontend
pnpm install
pnpm dev
```

## Estrutura

```
backend/
  app/
    main.py              # raiz de composição: registra módulos, middleware e erros
    shared/              # configuração, banco, logs, erros, Celery, saúde
    modules/<modulo>/    # um pacote por módulo de negócio
      api.py             # rotas HTTP
      service.py         # interface pública para outros módulos
      (domain.py, models.py, repository.py, ports.py, tasks.py conforme o módulo cresce)
    adapters/            # implementações de infraestrutura das portas (LLM, storage, e-mail...)
  migrations/            # Alembic
  prompts/               # prompts versionados
  tests/
frontend/                # React + TypeScript + Vite + Tailwind
extension/               # extensão de navegador (sprint 12)
deploy/                  # configuração do servidor do piloto (sprint 14)
```

### Regras de fronteira (verificadas no CI)

1. Um módulo só usa de outro módulo o pacote raiz ou o `service.py` (`tests/test_arquitetura.py`).
2. Módulos não importam `app.adapters`; recebem as implementações pela raiz de composição (`lint-imports`).
3. `app.shared` não importa módulos nem adaptadores.
4. Adaptadores específicos de um módulo (ex.: leitor de Excel) ficam dentro do próprio módulo.

### Regras de privacidade no código

- Nunca registrar em log texto de clientes (perguntas, respostas, arquivos, chat). Só ids, contagens e códigos.
- Erros de validação não devolvem o valor recebido.
- Dados de teste são sintéticos.

## Convenções

- Branches curtas `feat/`, `fix/`, `chore/` a partir de `main`; Conventional Commits.
- Um PR por tarefa, com a definição de pronto do plano.
- Tag ao fim de cada sprint (`v0.1.0` = sprint 1).
- `pre-commit install` para rodar ruff, mypy, import-linter e prettier antes de cada commit.
