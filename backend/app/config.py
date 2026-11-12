from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    waha_url: str = "http://waha:3000"
    waha_api_key: str = ""
    backend_internal_url: str = "http://backend:8000"
    webhook_secret: str = "change-me"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 12
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
