from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    waha_url: str = "http://waha:3000"
    waha_api_key: str = ""
    # Dirección (vista desde el navegador) del dashboard de WAHA, para la pestaña "WAHA" del panel
    waha_public_url: str = "http://localhost:3001"
    backend_internal_url: str = "http://backend:8000"
    webhook_secret: str = "change-me"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 12
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"
    cors_origins: str = "http://localhost:5173"
    # Dominios de las landings que llaman a /track/click (separados por coma)
    landing_origins: str = ""
    # Meta Conversions API (Pixel). Sin estos datos los eventos quedan en "not_configured".
    meta_pixel_id: str = ""
    meta_access_token: str = ""
    meta_api_version: str = "v21.0"
    meta_test_event_code: str = ""  # para probar en "Probar eventos" del Administrador de eventos
    meta_default_currency: str = "ARS"


@lru_cache
def get_settings() -> Settings:
    return Settings()
