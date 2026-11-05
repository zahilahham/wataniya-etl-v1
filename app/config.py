from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_dsn: str
    oracle_user: str = ""
    oracle_password: str = ""
    oracle_dsn: str = ""
    kstl_schema: str = "PULSE_NFC_PROD"
    log_dir: Path = PROJECT_ROOT / "logs"
    sql_dir: Path = PROJECT_ROOT / "sql_transformation"
    extract_batch_size: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
