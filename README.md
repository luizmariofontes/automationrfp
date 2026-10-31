# RFP Automation

Automação de preenchimento de RFPs e RFIs com IA. Responde questionários em Excel ou web a partir de uma base de documentos (RAG) e de uma biblioteca de respostas aprovadas, distribui validações por equipe com cobrança de prazos, oferece um chat por requisição espelhado por e-mail e expurga o arquivo original ao concluir.

Arquitetura e plano: documento "Plano de Implementação do Piloto — Automação RFP/RFI" (abas *Arquitetura* e *Plano de execução*).

## Estado atual

- **Sprint 1 — Esqueleto (concluído, `v0.1.0`).** Estrutura de módulos, API com saúde e erros padronizados, logs JSON, banco com migrações, Celery, Docker Compose, CI e front-end base.
- **Sprint 2 — em andamento.** Login local para testes (`v0.2.0-alpha`): usuários, papéis, sessões, tela de login e proteção de rotas. Falta: SSO, auditoria, cadastros e telas de administração.

## Como rodar (Windows, PowerShell)

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto e Git. Nada mais precisa ser instalado: Python, Node e bancos rodam nos containers.

```powershell
.\dev.ps1 setup    # primeira vez: cria o .env, sobe tudo, aplica as migrações e cria os usuários de teste
.\dev.ps1 up       # nas próximas vezes
.\dev.ps1 test     # testes do backend e do front
.\dev.ps1 lint     # ruff, mypy, import-linter e lint do front
.\dev.ps1 ajuda    # todos os comandos
```

Se o Windows bloquear o script ("execução de scripts foi desabilitada"), rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

No Linux, macOS ou WSL, os mesmos comandos existem no `Makefile` (`make setup`, `make up`, `make test`...).

### Login local para testes

O `setup` (ou `.\dev.ps1 seed`) cria um usuário por papel, todos com a senha `rfp-local-123`:

| E-mail | Papel |
| --- | --- |
| admin@rfp.local | Administrador (acesso a tudo) |
| analista@rfp.local | Analista |
| validador@rfp.local | Validador |
| conhecimento@rfp.local | Gestor de conhecimento |

O login local é controlado por `AUTH_LOCAL_ENABLED` no `.env`. Com `APP_ENV=producao`, a aplicação se recusa a iniciar se ele estiver ligado; lá o acesso será só pelo SSO da empresa. Após 5 senhas erradas seguidas, o usuário fica bloqueado por 15 minutos.

| Serviço | Endereço |
| --- | --- |
| Interface | http://localhost:5173 |
| API (documentação OpenAPI) | http://localhost:8000/api/docs |
| Saúde das dependências | http://localhost:8000/api/v1/health/ready |
| Console do MinIO | http://localhost:9001 |
| E-mails capturados (Mailpit) | http://localhost:8025 |

### Sem Docker

Precisa de Python 3.12 com [uv](https://docs.astral.sh/uv/), Node 22 com pnpm, Postgres 16 com pgvector e Redis. Funciona no PowerShell e no Linux:

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload
# em outro terminal:
uv run celery -A app.shared.celery_app worker -Q default,cobranca -l info --pool solo

cd ..\frontend
pnpm install
pnpm dev
```

No Windows, o Celery precisa de `--pool solo` fora do Docker.

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
