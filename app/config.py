from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Jamly API"
    database_url: str = "sqlite:///./jamly.db"
    upload_dir: str = "uploads"
    analysis_mode: str = "inline"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
