from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://telivex:telivex_dev@localhost:5433/telivex"

    # Storage
    storage_path: str = "./storage/uploads"

    # API
    api_prefix: str = "/api/v1"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
