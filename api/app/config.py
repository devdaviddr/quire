from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, all of it from the environment.

    The contextual detector is the only stage that needs an API key. Every
    other stage — ingest, the pattern and checksum rules, the rulebook, and
    the output pipeline — runs offline, which is what makes the exemption
    proposals reproducible and testable without a model in the loop.
    """

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    database_url: str = Field(
        "postgresql+psycopg://quire:quire@db:5432/quire", alias="DATABASE_URL"
    )
    data_dir: Path = Field(Path("/data"), alias="QUIRE_DATA_DIR")
    llm_model: str = Field("claude-opus-5", alias="QUIRE_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")


settings = Settings()
