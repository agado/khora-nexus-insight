import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"
_PLACEHOLDER_JWT_SECRET = "CHANGE_ME_PROD_JWT_SECRET_64chars_minimum"
_FORBIDDEN_JWT_SECRETS = frozenset({_DEFAULT_JWT_SECRET, _PLACEHOLDER_JWT_SECRET})


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./nexus.db"
    ollama_host: str = "http://ollama_service:11434"
    model_name: str = "qwen2.5:1.5b"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    admin_username: str = "admin"
    company_name: str = "Your Company"
    nexus_env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def check_jwt_secret(env: str | None = None) -> None:
    if settings.jwt_secret in _FORBIDDEN_JWT_SECRETS:
        actual_env = env if env is not None else os.environ.get("NEXUS_ENV", "development").lower()
        logger = logging.getLogger("nexus")
        if actual_env == "production":
            raise RuntimeError(
                "JWT_SECRET no puede ser un valor por defecto o placeholder en producción. "
                "Establece JWT_SECRET en .env o variables de entorno."
            )
        logger.warning(
            "JWT_SECRET usando valor por defecto/placeholder (inseguro para producción). "
            "Establece JWT_SECRET en .env o variables de entorno."
        )
