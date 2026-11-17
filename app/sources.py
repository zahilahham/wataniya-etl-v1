from __future__ import annotations

from app.config import Settings


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
