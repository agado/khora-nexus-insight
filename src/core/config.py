from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./nexus.db"
    ollama_host: str = "http://ollama_service:11434"
    model_name: str = "qwen2.5-coder:1.5b"
    jwt_secret: str = "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    admin_username: str = "admin"
    company_name: str = "Global Solutions Corp"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
