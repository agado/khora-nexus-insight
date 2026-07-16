from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_host: str = "http://ollama_service:11434"
    model_name: str = "qwen2.5-coder:1.5b"

    class Config:
        env_file = ".env"


settings = Settings()
