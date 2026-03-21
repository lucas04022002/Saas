from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {"change-me", "change-me-cron", ""}


class Settings(BaseSettings):
    app_name: str = "RushPlay API"
    env: str = "development"
    port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rushplay"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cron_secret: str

    @field_validator("jwt_secret", "cron_secret")
    @classmethod
    def _require_secure_secret(cls, v: str, info) -> str:
        if v in _INSECURE_DEFAULTS or len(v) < 16:
            raise ValueError(
                f"{info.field_name} must be set to a secure random value (min 16 chars). "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v
    cors_origins: str = "http://localhost:3000"
    prediction_provider: str = Field(default="local", pattern="^(mock|local)$")
    prediction_model_root: str | None = None
    api_football_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
