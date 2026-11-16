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
    stg_sqlserver_host: str = ""
    stg_sqlserver_port: int = 1433
    stg_sqlserver_database: str = ""
    stg_sqlserver_user: str = ""
    stg_sqlserver_password: str = ""
    stg_sqlserver_encrypt: bool = True
    stg_sqlserver_trust_server_certificate: bool = True
    vault_sqlserver_host: str = ""
    vault_sqlserver_port: int = 1433
    vault_sqlserver_database: str = ""
    vault_sqlserver_user: str = ""
    vault_sqlserver_password: str = ""
    vault_sqlserver_encrypt: bool = True
    vault_sqlserver_trust_server_certificate: bool = True
    log_dir: Path = PROJECT_ROOT / "logs"
    sql_dir: Path = PROJECT_ROOT / "sql_transformation"
    extract_batch_size: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
