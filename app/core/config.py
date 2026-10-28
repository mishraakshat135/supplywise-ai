"""Central configuration. Every setting can be overridden from the .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SupplyWise AI"
    debug: bool = True

    database_url: str = "sqlite:///./supplywise.db"
    auto_create_tables: bool = True

    # TODO(INTEGRATION: FRONTEND): add the real React URL(s) in .env -> CORS_ORIGINS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    default_coverage_days: int = 14
    default_order_budget: float = 100000
    approval_threshold: float = 50000
    min_history_days: int = 30

    model_dir: str = "./data/models"
    forecast_backend: str = "auto"  # auto | moving_average | sklearn

    upload_dir: str = "./data/uploads"
    retriever_backend: str = "keyword"  # keyword | chroma
    chroma_dir: str = "./data/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    llm_backend: str = "template"  # template | anthropic
    llm_model: str = "claude-sonnet-5-5"
    anthropic_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
