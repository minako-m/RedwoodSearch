from pydantic_settings import BaseSettings, SettingsConfigDict


class DbSettings(BaseSettings):
    """Database URLs, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://redwood:redwood@localhost:5433/redwood"
    # Tests wipe and rebuild this database; never point it at real data.
    test_database_url: str = "postgresql://redwood:redwood@localhost:5433/redwood_test"


db_settings = DbSettings()
