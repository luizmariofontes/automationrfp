"""Configuração da aplicação, lida de variáveis de ambiente (ver .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "homologacao", "producao"] = "local"
    app_name: str = "RFP Automation"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+psycopg://rfp:rfp@localhost:5432/rfp"
    redis_url: str = "redis://localhost:6379/0"
    # Papel do Postgres usado pelo agente: só lê o schema `agente` (ver app/shared/db.py).
    agente_db_role: str = Field(default="rfp_agente", pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    # Login próprio do agente. Vazio: usa DATABASE_URL e assume o papel com SET ROLE,
    # o que basta no ambiente local. Fora dele, use um login que só tenha esse papel.
    agente_database_url: str = ""

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "rfp"
    minio_secret_key: str = Field(default="rfp-secret-local", repr=False)
    minio_bucket_originais: str = "originais"
    minio_bucket_documentos: str = "documentos"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "rfp-automation@localhost"

    llm_provider: Literal["fake", "anthropic", "openai", "bedrock", "azure"] = "fake"
    llm_model: str = ""
    # Política de envio de dados ao provedor (ver app/shared/llm.py).
    # Chave geral: false impede qualquer chamada ao modelo.
    llm_enabled: bool = True
    # O que o contrato com o provedor garante. É uma declaração, não uma verificação.
    llm_retencao: Literal["padrao", "zero"] = "padrao"
    # true recusa provedor externo sem retenção zero declarada.
    llm_exige_retencao_zero: bool = False
    # false retém a classe de dado quando o provedor é externo.
    llm_envia_trechos_base: bool = True
    llm_envia_memoria: bool = True
    embedding_provider: Literal["fake", "local"] = "fake"

    cors_origins: list[str] = ["http://localhost:5173"]

    # Tempo máximo das checagens de prontidão (segundos)
    readiness_timeout: float = 2.0

    # ------------------------------------------------------------ autenticação
    # Login local (e-mail e senha) para testes. Proibido em produção: lá só SSO.
    auth_local_enabled: bool = True
    # SSO (OIDC) entra quando o provedor da empresa for configurado.
    auth_oidc_enabled: bool = False
    session_cookie_name: str = "rfp_sessao"
    session_ttl_hours: int = 12
    # Em produção e homologação o cookie só trafega por HTTPS.
    session_cookie_secure: bool = False
    login_max_falhas: int = 5
    login_bloqueio_minutos: int = 15
    # Senha dos usuários de exemplo criados pelo seed (apenas ambiente local).
    seed_password: str = Field(default="rfp-local-123", repr=False)

    @model_validator(mode="after")
    def _regras_de_ambiente(self) -> "Settings":
        if self.app_env == "producao":
            if self.auth_local_enabled:
                raise ValueError("AUTH_LOCAL_ENABLED não pode ser true em produção (use SSO).")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE deve ser true em produção.")
        if self.llm_provider != "fake":
            if not self.llm_model:
                raise ValueError("LLM_MODEL é obrigatório quando LLM_PROVIDER não é fake.")
            if self.llm_exige_retencao_zero and self.llm_retencao != "zero":
                raise ValueError(
                    "LLM_EXIGE_RETENCAO_ZERO=true exige LLM_RETENCAO=zero para provedor externo."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
