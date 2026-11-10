import secrets
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
    # Set a persistent secret in production, especially with multiple workers.
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48), min_length=32)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
