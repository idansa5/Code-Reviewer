from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_timeout_seconds: int = 120
    max_parallel_scans: int = 5
    result_ttl_hours: int = 24
    database_url: str = "sqlite+aiosqlite:///./code_review.db"
    rules_version: str = "v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
