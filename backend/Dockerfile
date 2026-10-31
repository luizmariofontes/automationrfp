# Backend: API (uvicorn), workers Celery e worker de cobrança usam esta mesma imagem.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas
COPY pyproject.toml uv.lock ./
ARG UV_GROUPS="--no-dev"
RUN uv sync --frozen ${UV_GROUPS}

COPY . .

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
