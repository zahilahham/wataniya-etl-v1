"""Check the PostgreSQL and Oracle logins in .env.

Run on the server, from the project folder:

    .venv/Scripts/python.exe check_connections.py

Prints ok or FAIL for each login. Passwords are not printed.
"""

from __future__ import annotations

import sys

from app.config import get_settings
from app.sources import connect_oracle


def scrub(message: str, secrets: list[str]) -> str:
    cleaned = " ".join(message.split())
    for secret in secrets:
        if secret:
            cleaned = cleaned.replace(secret, "<redacted>")
    return cleaned[:300]


def check(name: str, connect, secrets: list[str]) -> None:
    try:
        connection = connect()
        connection.close()
    except Exception as exc:
        print(name, "FAIL", type(exc).__name__ + ":", scrub(str(exc), secrets))
        return
    print(name, "ok")


def main() -> None:
    settings = get_settings()
    secrets = [settings.oracle_password, settings.postgres_dsn]
    check("postgres", lambda: __import__("psycopg").connect(settings.postgres_dsn), secrets)
    check("oracle", lambda: connect_oracle(settings), secrets)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
