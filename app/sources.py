from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings

_SQLSERVER_DRIVERS = (
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
)


@dataclass(frozen=True)
class SqlServerTarget:
    name: str
    host: str
    port: int
    database: str
    user: str
    password: str
    encrypt: bool
    trust_server_certificate: bool


def connect_oracle(settings: Settings):
    missing = [
        label
        for label, value in (
            ("ORACLE_USER", settings.oracle_user),
            ("ORACLE_PASSWORD", settings.oracle_password),
            ("ORACLE_DSN", settings.oracle_dsn),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} must be set before connecting to Kastle")
    import oracledb

    oracledb.defaults.fetch_decimals = True
    return oracledb.connect(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
    )


def stg_target(settings: Settings) -> SqlServerTarget:
    return SqlServerTarget(
        name="STG",
        host=settings.stg_sqlserver_host,
        port=settings.stg_sqlserver_port,
        database=settings.stg_sqlserver_database,
        user=settings.stg_sqlserver_user,
        password=settings.stg_sqlserver_password,
        encrypt=settings.stg_sqlserver_encrypt,
        trust_server_certificate=settings.stg_sqlserver_trust_server_certificate,
    )


def vault_target(settings: Settings) -> SqlServerTarget:
    return SqlServerTarget(
        name="VAULT",
        host=settings.vault_sqlserver_host,
        port=settings.vault_sqlserver_port,
        database=settings.vault_sqlserver_database,
        user=settings.vault_sqlserver_user,
        password=settings.vault_sqlserver_password,
        encrypt=settings.vault_sqlserver_encrypt,
        trust_server_certificate=settings.vault_sqlserver_trust_server_certificate,
    )


def connect_sqlserver(target: SqlServerTarget):
    missing = [
        label
        for label, value in (
            ("host", target.host),
            ("database", target.database),
            ("user", target.user),
            ("password", target.password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"{target.name} is missing {', '.join(missing)}")
    import pyodbc

    return pyodbc.connect(sqlserver_odbc_connection_string(target, driver=_sqlserver_driver(pyodbc.drivers())))


def sqlserver_odbc_connection_string(target: SqlServerTarget, driver: str) -> str:
    encrypt = "yes" if target.encrypt else "no"
    trust = "yes" if target.trust_server_certificate else "no"
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={target.host},{target.port};"
        f"DATABASE={target.database};"
        f"UID={target.user};"
        f"PWD={target.password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust}"
    )


def _sqlserver_driver(installed: list[str]) -> str:
    for name in _SQLSERVER_DRIVERS:
        if name in installed:
            return name
    raise RuntimeError("Install ODBC Driver 18 for SQL Server")
