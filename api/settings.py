from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://redwood:redwood@localhost:5432/redwood"
    anthropic_api_key: SecretStr | None = None
    # Temporary until the database exists (Step 2): courses are served from `make fetch` output.
    raw_catalog_dir: Path = Path("data/raw/2026-2027")


settings = Settings()
