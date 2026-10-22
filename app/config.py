from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agent_eval.db"
    worker_poll_seconds: float = 1.0
    execution_timeout_seconds: int = 15
    auto_create_tables: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
