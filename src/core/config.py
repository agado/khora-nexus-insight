import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./nexus.db"
    ollama_host: str = "http://ollama_service:11434"
    model_name: str = "qwen2.5:1.5b"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    admin_username: str = "admin"
    company_name: str = "Your Company"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def check_jwt_secret() -> None:
    if settings.jwt_secret == _DEFAULT_JWT_SECRET:
        logger = logging.getLogger("nexus")
        logger.warning(
            "JWT_SECRET usando valor por defecto (inseguro para producción). "
            "Establece JWT_SECRET en .env o variables de entorno."
        )
