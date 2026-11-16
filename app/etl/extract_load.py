from __future__ import annotations

import re
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from psycopg import Connection, sql

from app.config import Settings
from app.logging_setup import RunLog
from app.sources import connect_oracle

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_PG_TYPES = {
    "DB_TYPE_VARCHAR": "text",
    "DB_TYPE_CHAR": "text",
    "DB_TYPE_NVARCHAR": "text",
    "DB_TYPE_NCHAR": "text",
    "DB_TYPE_LONG": "text",
    "DB_TYPE_CLOB": "text",
    "DB_TYPE_NCLOB": "text",
    "DB_TYPE_NUMBER": "numeric",
    "DB_TYPE_DATE": "timestamp",
    "DB_TYPE_TIMESTAMP": "timestamp",
    "DB_TYPE_TIMESTAMP_TZ": "timestamp",
    "DB_TYPE_TIMESTAMP_LTZ": "timestamp",
    "DB_TYPE_BINARY_FLOAT": "double precision",
    "DB_TYPE_BINARY_DOUBLE": "double precision",
    "DB_TYPE_RAW": "bytea",
    "DB_TYPE_LONG_RAW": "bytea",
    "DB_TYPE_BLOB": "bytea",
}


def map_oracle_type(type_code: object) -> str:
    name = getattr(type_code, "name", "")
    return _PG_TYPES.get(name, "text")


def extract_employee(
    conn: Connection,
    run_log: RunLog,
    start_dt: date,
    end_dt: date,
    settings: Settings,
) -> int:
    schema = _oracle_schema(settings.kstl_schema)
    end_exclusive = end_dt + timedelta(days=1)
    query = (
        f"SELECT * FROM {schema}.EMPLOYEE "
        "WHERE MAKEDATE >= :start_dt AND MAKEDATE < :end_dt_exclusive"
    )
    run_log.event(
        "INFO",
        "connect_oracle",
        f"Connecting to Oracle for {schema}.EMPLOYEE "
        f"window {start_dt.isoformat()} to {end_dt.isoformat()}",
    )
    started = time.perf_counter()
    with connect_oracle(settings) as source:
        run_log.event(
            "INFO",
            "connect_oracle",
            "Oracle connection ready",
            duration_ms=_elapsed_ms(started),
        )
        with source.cursor() as source_cursor:
            source_cursor.arraysize = settings.extract_batch_size
            run_log.event("INFO", "query", query)
            query_started = time.perf_counter()
            source_cursor.execute(
                query,
                {"start_dt": start_dt, "end_dt_exclusive": end_exclusive},
            )
            columns = _columns(source_cursor.description, run_log)
            run_log.event(
                "INFO",
                "query",
                "Oracle query opened. Columns: " + ", ".join(
                    f"{name} {pg_type}" for name, pg_type in columns
                ),
                duration_ms=_elapsed_ms(query_started),
            )
            _ensure_raw_employee(conn, columns, run_log)
            return _copy_rows(conn, source_cursor, columns, run_log, settings.extract_batch_size)


def _oracle_schema(name: str) -> str:
    if not _IDENTIFIER.fullmatch(name):
        raise ValueError("KSTL_SCHEMA is not a safe Oracle identifier")
    return name


def _columns(description: list[Any] | None, run_log: RunLog) -> list[tuple[str, str]]:
    if not description:
        raise RuntimeError("Oracle did not return a column list for EMPLOYEE")
    columns: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in description:
        name = str(item[0]).lower()
        if not _IDENTIFIER.fullmatch(name):
            raise ValueError(f"Unsupported Oracle column name: {item[0]}")
        if name in seen:
            raise ValueError(f"Duplicate column name after lowercasing: {name}")
        seen.add(name)
        pg_type = map_oracle_type(item[1])
        if pg_type == "text" and getattr(item[1], "name", "") not in _PG_TYPES:
            run_log.event(
                "INFO",
                "column_type",
                f"Column {name} uses Oracle type {getattr(item[1], 'name', item[1])}; stored as text",
            )
        columns.append((name, pg_type))
    return columns


def _ensure_raw_employee(
    conn: Connection,
    columns: list[tuple[str, str]],
    run_log: RunLog,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'raw' AND table_name = 'employee'
            ORDER BY ordinal_position
            """
        )
        existing = [row["column_name"] for row in cur.fetchall()]
    names = [name for name, _ in columns]
    if existing:
        if existing != names:
            raise RuntimeError(
                "raw.employee columns do not match this Oracle extract. "
                f"database={existing} oracle={names}"
            )
        run_log.event("INFO", "raw_table", "raw.employee already exists")
        return

    definitions = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(pg_type))
        for name, pg_type in columns
    )
    statement = sql.SQL("CREATE TABLE raw.employee ({})").format(definitions)
    with conn.cursor() as cur:
        cur.execute(statement)
    conn.commit()
    run_log.event(
        "INFO",
        "raw_table",
        "Created raw.employee (" + ", ".join(f"{name} {pg_type}" for name, pg_type in columns) + ")",
    )


def _copy_rows(
    conn: Connection,
    source_cursor: Any,
    columns: list[tuple[str, str]],
    run_log: RunLog,
    batch_size: int,
) -> int:
    column_names = [name for name, _ in columns]
    copy_sql = sql.SQL("COPY raw.employee ({}) FROM STDIN").format(
        sql.SQL(", ").join(sql.Identifier(name) for name in column_names)
    )
    with conn.cursor() as cur:
        truncate_started = time.perf_counter()
        cur.execute("TRUNCATE TABLE raw.employee")
    conn.commit()
    run_log.event(
        "INFO",
        "truncate",
        "Truncated raw.employee",
        duration_ms=_elapsed_ms(truncate_started),
    )
    total = 0
    batch_number = 0
    while True:
        fetched = source_cursor.fetchmany(batch_size)
        if not fetched:
            break
        batch_number += 1
        batch_started = time.perf_counter()
        with conn.cursor() as cur:
            with cur.copy(copy_sql) as copy:
                for row in fetched:
                    copy.write_row(_adapt_row(row))
        conn.commit()
        total += len(fetched)
        run_log.event(
            "INFO",
            "load_batch",
            f"Copied batch {batch_number} into raw.employee (total {total})",
            rows=len(fetched),
            duration_ms=_elapsed_ms(batch_started),
        )
    run_log.event(
        "INFO",
        "commit",
        f"Committed {total} rows into raw.employee",
        rows=total,
    )
    return total


def _adapt_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(_adapt_value(value) for value in row)


def _adapt_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bytes, int, float, Decimal, date)):
        return value
    reader = getattr(value, "read", None)
    if callable(reader):
        return reader()
    return value


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
