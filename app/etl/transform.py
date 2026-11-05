from __future__ import annotations

import time
from datetime import date
from pathlib import Path

from psycopg import Connection

from app.logging_setup import RunLog

SQL_FILE_NAME = "V1__transformation_job.sql"


def execute_sql_transformations(
    connection: Connection,
    run_log: RunLog,
    start_dt: date,
    end_dt: date,
    sql_dir: Path,
) -> None:
    """Read V1 transformation files in folder order and execute each statement."""
    _set_window(connection, start_dt, end_dt)
    run_log.event(
        "INFO",
        "transform_window",
        f"Session window set to {start_dt.isoformat()} through {end_dt.isoformat()}",
    )
    files = list_transformation_files(sql_dir)
    if not files:
        run_log.event("INFO", "transform", f"No {SQL_FILE_NAME} files under {sql_dir}")
        return

    for path in files:
        relative = f"{path.parent.name}/{path.name}"
        script = path.read_text(encoding="utf-8")
        statements = [item for item in split_sql(script) if _is_executable(item)]
        if not statements:
            run_log.event(
                "INFO",
                "transform_skip",
                f"Skipped empty transformation file {relative}",
                sql_file=relative,
            )
            continue
        run_log.event(
            "INFO",
            "transform_file",
            f"Starting {relative} ({len(statements)} statements)",
            sql_file=relative,
        )
        for number, statement in enumerate(statements, start=1):
            _execute_statement(connection, run_log, relative, number, statement)
        run_log.event(
            "INFO",
            "transform_file",
            f"Finished {relative}",
            sql_file=relative,
        )


def list_transformation_files(sql_dir: Path) -> list[Path]:
    if not sql_dir.is_dir():
        return []
    return sorted(sql_dir.glob(f"*/{SQL_FILE_NAME}"), key=lambda path: path.parent.name.lower())


def split_sql(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    index = 0
    length = len(script)
    while index < length:
        char = script[index]
        nxt = script[index + 1] if index + 1 < length else ""
        if char == "-" and nxt == "-":
            end = script.find("\n", index)
            if end == -1:
                current.append(script[index:])
                break
            current.append(script[index : end + 1])
            index = end + 1
            continue
        if char == "/" and nxt == "*":
            end = script.find("*/", index + 2)
            if end == -1:
                current.append(script[index:])
                break
            current.append(script[index : end + 2])
            index = end + 2
            continue
        if char == "'":
            index = _consume_quoted(script, index, current, "'")
            continue
        if char == '"':
            index = _consume_quoted(script, index, current, '"')
            continue
        if char == "$":
            tag = _dollar_tag(script, index)
            if tag is not None:
                end = script.find(tag, index + len(tag))
                if end == -1:
                    current.append(script[index:])
                    break
                end += len(tag)
                current.append(script[index:end])
                index = end
                continue
        if char == ";":
            text = "".join(current).strip()
            if text:
                statements.append(text)
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _execute_statement(
    connection: Connection,
    run_log: RunLog,
    sql_file: str,
    number: int,
    statement: str,
) -> None:
    preview = _preview(statement)
    started = time.perf_counter()
    try:
        with connection.cursor() as cur:
            cur.execute(statement)
            rowcount = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else None
        connection.commit()
    except Exception as exc:
        connection.rollback()
        run_log.event(
            "ERROR",
            "transform_statement",
            f"Statement {number} failed: {exc}. SQL: {preview}",
            duration_ms=_elapsed_ms(started),
            sql_file=sql_file,
        )
        raise
    run_log.event(
        "INFO",
        "transform_statement",
        f"Statement {number} ok: {preview}",
        rows=rowcount,
        duration_ms=_elapsed_ms(started),
        sql_file=sql_file,
    )


def _set_window(connection: Connection, start_dt: date, end_dt: date) -> None:
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('etl.start_dt', %s, false)", (start_dt.isoformat(),))
        cur.fetchone()
        cur.execute("SELECT set_config('etl.end_dt', %s, false)", (end_dt.isoformat(),))
        cur.fetchone()
    connection.commit()


def _consume_quoted(script: str, index: int, current: list[str], quote: str) -> int:
    current.append(quote)
    index += 1
    length = len(script)
    while index < length:
        char = script[index]
        current.append(char)
        index += 1
        if char == quote:
            if index < length and script[index] == quote:
                current.append(script[index])
                index += 1
                continue
            break
    return index


def _dollar_tag(script: str, index: int) -> str | None:
    if script[index] != "$":
        return None
    end = index + 1
    length = len(script)
    while end < length and (script[end].isalnum() or script[end] == "_"):
        end += 1
    if end < length and script[end] == "$":
        return script[index : end + 1]
    return None


def _is_executable(statement: str) -> bool:
    kept: list[str] = []
    index = 0
    length = len(statement)
    while index < length:
        char = statement[index]
        nxt = statement[index + 1] if index + 1 < length else ""
        if char == "-" and nxt == "-":
            end = statement.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        if char == "/" and nxt == "*":
            end = statement.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue
        if char in {"'", '"'}:
            buffer: list[str] = []
            index = _consume_quoted(statement, index, buffer, char)
            kept.extend(buffer)
            continue
        if char == "$":
            tag = _dollar_tag(statement, index)
            if tag is not None:
                end = statement.find(tag, index + len(tag))
                index = length if end == -1 else end + len(tag)
                kept.append("x")
                continue
        kept.append(char)
        index += 1
    return any(not char.isspace() for char in kept)


def _preview(statement: str) -> str:
    compact = " ".join(statement.split())
    if len(compact) <= 200:
        return compact
    return compact[:200] + "..."


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
