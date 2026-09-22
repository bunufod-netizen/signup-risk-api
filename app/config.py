from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    dns_timeout_seconds: float = 3.0
    dns_retries: int = 1
    max_bulk_emails: int = 100
    max_request_body_bytes: int = 32_768
    rapidapi_proxy_secret: str | None = None
    port: int = 8000
    cors_origins: str = ""
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
