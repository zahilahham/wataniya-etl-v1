from __future__ import annotations

import re
import threading
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

import psycopg

from app.config import get_settings
from app.db import connect

_file_lock = threading.Lock()
_DSN_PASSWORD = re.compile(r"://([^:/@]+):([^@]+)@")


def redact(text: str) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    settings = get_settings()
    for secret in (settings.postgres_dsn, settings.oracle_password):
        if secret:
            cleaned = cleaned.replace(secret, "***")
    return _DSN_PASSWORD.sub(r"://\1:***@", cleaned)


class RunLog:
    """Write one run's events to the daily file and to etl.run_event."""

    def __init__(self, run_id: UUID):
        self.run_id = run_id
        self._settings = get_settings()
        self._conn = connect()
        self._conn.autocommit = True

    def close(self) -> None:
        self._conn.close()

    def event(
        self,
        level: str,
        step: str,
        message: str,
        *,
        rows: int | None = None,
        duration_ms: int | None = None,
        sql_file: str | None = None,
    ) -> None:
        message = redact(message)
        logged_at = datetime.now().astimezone()
        self._write_file(logged_at, level, step, message, rows, duration_ms, sql_file)
        self._conn.execute(
            """
            INSERT INTO etl.run_event (
                run_id, logged_at, level, step, message, rows, duration_ms, sql_file
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (self.run_id, logged_at, level, step, message, rows, duration_ms, sql_file),
        )

    def set_status(self, status: str, error: str | None = None) -> None:
        error_text = redact(error) if error else None
        if status == "running":
            self._conn.execute(
                """
                UPDATE etl.run
                SET status = %s,
                    started_at = COALESCE(started_at, now()),
                    error = NULL
                WHERE run_id = %s
                """,
                (status, self.run_id),
            )
            return
        if status in {"success", "failed"}:
            self._conn.execute(
                """
                UPDATE etl.run
                SET status = %s, finished_at = now(), error = %s
                WHERE run_id = %s
                """,
                (status, error_text, self.run_id),
            )
            return
        self._conn.execute(
            "UPDATE etl.run SET status = %s, error = %s WHERE run_id = %s",
            (status, error_text, self.run_id),
        )

    def _write_file(
        self,
        logged_at: datetime,
        level: str,
        step: str,
        message: str,
        rows: int | None,
        duration_ms: int | None,
        sql_file: str | None,
    ) -> None:
        log_dir = self._settings.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"etl-{logged_at.date().isoformat()}.log"
        parts = [
            logged_at.isoformat(timespec="seconds"),
            level,
            f"run={self.run_id}",
            f"step={step}",
            message,
        ]
        if rows is not None:
            parts.append(f"rows={rows}")
        if duration_ms is not None:
            parts.append(f"duration_ms={duration_ms}")
        if sql_file:
            parts.append(f"sql_file={sql_file}")
        line = " ".join(parts) + "\n"
        with _file_lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)


def daily_log_file(day: date | None = None) -> Path:
    selected = day or datetime.now().astimezone().date()
    return get_settings().log_dir / f"etl-{selected.isoformat()}.log"


def safe_db_error(exc: Exception) -> str:
    if isinstance(exc, psycopg.Error):
        return redact(str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__)
    return redact(str(exc))
