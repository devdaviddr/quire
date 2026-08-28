from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, all of it from the environment.

    Local-first: every stage except contextual detection runs on this machine
    with no network. The detector talks to an OpenAI-compatible endpoint, which
    is either NVIDIA NIM (hosted, the default) or a local server such as
    llama.cpp or Ollama. Only `llm_base_url` changes between the two.
    """

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    database_url: str = Field(
        "postgresql+psycopg://quire:quire@db:5432/quire", alias="DATABASE_URL"
    )
    data_dir: Path = Field(Path("/data"), alias="QUIRE_DATA_DIR")

    # Contextual detector (pipeline stage 3c).
    llm_base_url: str = Field(
        "https://integrate.api.nvidia.com/v1", alias="QUIRE_LLM_BASE_URL"
    )
    llm_model: str = Field("nvidia/nemotron-3-super-120b-a12b", alias="QUIRE_LLM_MODEL")
    llm_api_key: str = Field("", alias="NVIDIA_API_KEY")

    # Nemotron emits reasoning before the answer; a small budget truncates the
    # span array mid-array and the page silently under-reports. Measured: a
    # dense page needs ~800 completion tokens, so this leaves real headroom.
    llm_max_tokens: int = Field(6000, alias="QUIRE_LLM_MAX_TOKENS")

    # The free NIM endpoints are rate-limited rather than token-billed, so
    # throughput is the constraint. Pages are detected concurrently up to this
    # bound, with backoff on 429.
    llm_concurrency: int = Field(4, alias="QUIRE_LLM_CONCURRENCY")
    llm_timeout_seconds: int = Field(120, alias="QUIRE_LLM_TIMEOUT")


settings = Settings()
