.DEFAULT_GOAL := help
COMPOSE := docker compose
BACKEND := $(COMPOSE) exec api

.PHONY: help setup env up down logs ps migrate migration seed test test-integration lint fmt eval fidelity shell-api

help: ## Lista os comandos
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

env: ## Cria o .env a partir do .env.example (se ainda não existir)
	@test -f .env || cp .env.example .env

setup: up ## Primeira vez: sobe tudo, migra e cria os usuários de teste
	@echo "Aguardando a API..."; for i in $$(seq 1 45); do curl -sf localhost:8000/health >/dev/null && break; sleep 2; done
	$(BACKEND) alembic upgrade head
	$(BACKEND) python -m app.seed

up: env ## Sobe todos os serviços
	$(COMPOSE) up -d --build
	@echo "API:      http://localhost:8000/api/docs"
	@echo "Front:    http://localhost:5173"
	@echo "MinIO:    http://localhost:9001"
	@echo "Mailpit:  http://localhost:8025"

down: ## Derruba os serviços (mantém os volumes)
	$(COMPOSE) down

logs: ## Acompanha os logs
	$(COMPOSE) logs -f --tail=100

ps: ## Estado dos serviços
	$(COMPOSE) ps

migrate: ## Aplica as migrações do Alembic
	$(BACKEND) alembic upgrade head

migration: ## Cria uma migração: make migration m="descricao"
	$(BACKEND) alembic revision --autogenerate -m "$(m)"

seed: ## Cria os usuários de teste (senha: rfp-local-123)
	$(BACKEND) python -m app.seed

test: ## Testes do backend e do front
	$(BACKEND) env REQUIRE_DB=1 pytest
	$(COMPOSE) exec frontend pnpm test

test-integration: ## Testes com Postgres, Redis e worker reais
	$(BACKEND) env REQUIRE_DB=1 RUN_INTEGRATION=1 CELERY_WORKER=1 pytest -m integration

lint: ## ruff, mypy, import-linter e checagem do front
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) mypy app
	$(BACKEND) lint-imports
	$(COMPOSE) exec frontend pnpm run lint

fmt: ## Formata o código
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .
	$(COMPOSE) exec frontend pnpm run format

eval: ## Avaliação da IA (implementado no sprint 7)
	@echo "eval: disponível a partir do sprint 7."

fidelity: ## Testes de fidelidade do Excel (implementado no sprint 5)
	@echo "fidelity: disponível a partir do sprint 5."

shell-api: ## Shell dentro do container da API
	$(BACKEND) bash
