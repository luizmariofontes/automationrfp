"""Configuração da aplicação, lida de variáveis de ambiente (ver .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "homologacao", "producao"] = "local"
    app_name: str = "RFP Automation"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+psycopg://rfp:rfp@localhost:5432/rfp"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "rfp"
    minio_secret_key: str = Field(default="rfp-secret-local", repr=False)
    minio_bucket_originais: str = "originais"
    minio_bucket_documentos: str = "documentos"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "rfp-automation@localhost"

    llm_provider: Literal["fake", "anthropic", "openai", "bedrock", "azure"] = "fake"
    embedding_provider: Literal["fake", "local"] = "fake"

    cors_origins: list[str] = ["http://localhost:5173"]

    # Tempo máximo das checagens de prontidão (segundos)
    readiness_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
