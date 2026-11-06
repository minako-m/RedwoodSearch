from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config, read from environment variables or a local .env file.

    Database URLs live in db.settings, since ingest/ needs them too.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: SecretStr | None = None
    # Temporary until the API reads from the database: courses are served from `make fetch` output.
    raw_catalog_dir: Path = Path("data/raw/2026-2027")


settings = Settings()
