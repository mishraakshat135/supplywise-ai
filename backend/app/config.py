"""Environment-based configuration. Nothing secret is hardcoded."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"), extra="ignore")

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./supplywise_dev.db"  # override with PostgreSQL in .env
    CORS_ORIGINS: str = "http://localhost:5173"

    AUTH_ENABLED: bool = False
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 480

    APPROVAL_THRESHOLD: float = 100000.0
    FORECAST_HORIZON_DAYS: int = 14

    FORECAST_PROVIDER: str = "baseline"  # baseline | external
    ML_PREDICT_CALLABLE: str = ""  # "package.module:function"

    AI_ENABLED: bool = True
    CHROMA_PERSIST_DIRECTORY: str = ""
    POLICY_COLLECTION: str = "supplywise_policy"  # same collection PolicyAnalystAgent reads
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_MB: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def chroma_dir(self) -> Path:
        return Path(self.CHROMA_PERSIST_DIRECTORY) if self.CHROMA_PERSIST_DIRECTORY else REPO_ROOT / "chroma_db"

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        return p if p.is_absolute() else BACKEND_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
