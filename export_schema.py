"""Write schema-snapshot.json from Oracle and PostgreSQL in .env.

Run from this project:

    .venv\\Scripts\\python.exe export_schema.py

Oracle is the only source. PostgreSQL is the data lake. The file has
column lists, keys, and view text. It has no passwords and no table rows.
If NiFi_Flow.json or PG_STG_*.json is in this folder, processor SQL from
those files is included too.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.jobs.catalog import _STAGING_OBJECTS  # noqa: E402
from app.sources import connect_oracle  # noqa: E402

MAX_SQL_CHARS = 400_000
SOURCE_NAMES = tuple(dict.fromkeys(_STAGING_OBJECTS))
SQL_RE = re.compile(r"(?is)\b(select|insert|update|delete|merge|with|create|truncate)\b")
SECRET_KEY_RE = re.compile(r"password|secret|token|credential", re.I)


def scrub(value: str) -> str:
    value = re.sub(r"://([^:/@]+):([^@]+)@", "://<redacted>@", value)
    value = re.sub(
        r"(?i)\b(pwd|password|user\s*id|uid)\s*=\s*[^;'\s]+",
        lambda match: f"{match.group(1)}=<redacted>",
        value,
    )
    value = re.sub(
        r"(?i)\b(password|pwd|secret)\s*:\s*('(?:''|[^'])*'|\"[^\"']*\"|\S+)",
        lambda match: f"{match.group(1)}=<redacted>",
        value,
    )
    return value


def clip_sql(value: str | None) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    text = scrub(str(value))
    if len(text) <= MAX_SQL_CHARS:
        return text, False
    return text[:MAX_SQL_CHARS], True


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if hasattr(value, "read"):
        return json_ready(value.read())
    return value


def safe_error(exc: BaseException) -> str:
    return scrub(f"{type(exc).__name__}: {exc}")[:800]


def oracle_type(data_type: str, length: Any, precision: Any, scale: Any) -> str:
    if data_type == "NUMBER" and precision is not None:
        return f"NUMBER({precision},{scale or 0})"
    if data_type in {"VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR", "RAW"} and length is not None:
        return f"{data_type}({length})"
    return data_type


def probe_postgres(settings: Any, notes: list[str]) -> dict[str, Any]:
    import psycopg

    try:
        with psycopg.connect(settings.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT current_database(), current_user,
                           inet_server_addr()::text, inet_server_port(), version()
                    """
                )
                database, user, host, port, version = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT n.nspname, c.relname, c.relkind, COALESCE(s.n_live_tup, 0)
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    LEFT JOIN pg_stat_all_tables s ON s.relid = c.oid
                    WHERE n.nspname IN ('raw', 'reportingdw', 'etl', 'public')
                      AND c.relkind IN ('r', 'v', 'm', 'p')
                    ORDER BY n.nspname, c.relname
                    """
                )
                relations = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT table_schema, table_name, ordinal_position, column_name,
                           data_type, character_maximum_length, numeric_precision,
                           numeric_scale, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema IN ('raw', 'reportingdw', 'etl', 'public')
                    ORDER BY table_schema, table_name, ordinal_position
                    """
                )
                columns = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT tc.table_schema, tc.table_name, tc.constraint_type, kcu.column_name, kcu.ordinal_position
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON kcu.constraint_name = tc.constraint_name
                     AND kcu.table_schema = tc.table_schema
                    WHERE tc.table_schema IN ('raw', 'reportingdw', 'etl', 'public')
                      AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                    ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position
                    """
                )
                keys = cursor.fetchall()
        kind = {"r": "TABLE", "v": "VIEW", "m": "MATERIALIZED VIEW", "p": "PARTITIONED TABLE"}
        objects: dict[tuple[str, str], dict[str, Any]] = {}
        for schema, name, relkind, rows in relations:
            objects[(schema, name)] = {
                "schema": schema,
                "name": name,
                "kind": kind.get(relkind, relkind),
                "rows": rows,
                "columns": [],
                "primary_key": [],
                "unique": [],
            }
        for schema, name, position, column, data_type, length, precision, scale, nullable, default in columns:
            target = objects.setdefault(
                (schema, name),
                {
                    "schema": schema,
                    "name": name,
                    "kind": "TABLE",
                    "rows": None,
                    "columns": [],
                    "primary_key": [],
                    "unique": [],
                },
            )
            target["columns"].append(
                {
                    "position": position,
                    "name": column,
                    "data_type": data_type,
                    "length": length,
                    "precision": precision,
                    "scale": scale,
                    "nullable": nullable == "YES",
                    "default": None if default is None else str(default)[:500],
                }
            )
        unique: dict[tuple[str, str, str], list[tuple[int, str]]] = defaultdict(list)
        for schema, name, constraint_type, column, position in keys:
            if (schema, name) not in objects:
                continue
            if constraint_type == "PRIMARY KEY":
                objects[(schema, name)]["primary_key"].append((position, column))
            else:
                unique[(schema, name, constraint_type)].append((position, column))
        for item in objects.values():
            item["primary_key"] = [column for _, column in sorted(item["primary_key"])]
        for (schema, name, _), pairs in unique.items():
            objects[(schema, name)]["unique"].append([column for _, column in sorted(pairs)])
        return {
            "ok": True,
            "error": None,
            "database": database,
            "user": user,
            "host": host,
            "port": port,
            "version": version,
            "objects": list(objects.values()),
        }
    except Exception as exc:
        notes.append("PostgreSQL was not read. " + safe_error(exc))
        return {"ok": False, "error": safe_error(exc), "objects": []}


def probe_oracle(settings: Any, notes: list[str]) -> dict[str, Any]:
    names = tuple(dict.fromkeys(name.upper() for name in SOURCE_NAMES))
    result: dict[str, Any] = {
        "ok": False,
        "error": None,
        "user": settings.oracle_user,
        "dsn": settings.oracle_dsn,
        "schema": settings.kstl_schema,
        "db_name": None,
        "service_name": None,
        "objects": [],
        "missing": list(names),
    }
    binds = {f"t{index}": name for index, name in enumerate(names)}
    in_list = ", ".join(f":t{index}" for index in range(len(names)))
    params = {"owner": settings.kstl_schema, **binds}
    try:
        with connect_oracle(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT USER, SYS_CONTEXT('USERENV','DB_NAME'), SYS_CONTEXT('USERENV','SERVICE_NAME')
                    FROM dual
                    """
                )
                result["user"], result["db_name"], result["service_name"] = cursor.fetchone()
                cursor.execute(
                    f"""
                    SELECT object_name, object_type
                    FROM all_objects
                    WHERE owner = :owner
                      AND object_type IN ('TABLE', 'VIEW')
                      AND object_name IN ({in_list})
                    """,
                    params,
                )
                found = {name: kind for name, kind in cursor.fetchall()}
                cursor.execute(
                    f"""
                    SELECT owner, synonym_name, table_owner, table_name
                    FROM all_synonyms
                    WHERE owner IN (:owner, 'PUBLIC')
                      AND synonym_name IN ({in_list})
                    ORDER BY CASE WHEN owner = :owner THEN 0 ELSE 1 END
                    """,
                    params,
                )
                synonyms: dict[str, tuple[str, str]] = {}
                for _owner, synonym_name, table_owner, table_name in cursor.fetchall():
                    if synonym_name not in found and synonym_name not in synonyms:
                        synonyms[synonym_name] = (table_owner, table_name)
                cursor.execute(
                    f"""
                    SELECT table_name, column_id, column_name, data_type, data_length,
                           data_precision, data_scale, nullable, data_default
                    FROM all_tab_columns
                    WHERE owner = :owner AND table_name IN ({in_list})
                    ORDER BY table_name, column_id
                    """,
                    params,
                )
                column_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT ac.table_name, ac.constraint_type, ac.constraint_name,
                           acc.position, acc.column_name, r.table_name, rc.column_name
                    FROM all_constraints ac
                    JOIN all_cons_columns acc
                      ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name
                    LEFT JOIN all_constraints r
                      ON r.owner = ac.r_owner AND r.constraint_name = ac.r_constraint_name
                    LEFT JOIN all_cons_columns rc
                      ON rc.owner = r.owner AND rc.constraint_name = r.constraint_name
                     AND rc.position = acc.position
                    WHERE ac.owner = :owner
                      AND ac.table_name IN ({in_list})
                      AND ac.constraint_type IN ('P', 'U', 'R')
                    ORDER BY ac.table_name, ac.constraint_name, acc.position
                    """,
                    params,
                )
                key_rows = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT view_name, text
                    FROM all_views
                    WHERE owner = :owner AND view_name IN ({in_list})
                    """,
                    params,
                )
                view_text = {name: text for name, text in cursor.fetchall()}
                for synonym_name, (table_owner, table_name) in synonyms.items():
                    cursor.execute(
                        """
                        SELECT column_id, column_name, data_type, data_length,
                               data_precision, data_scale, nullable, data_default
                        FROM all_tab_columns
                        WHERE owner = :owner AND table_name = :table_name
                        ORDER BY column_id
                        """,
                        {"owner": table_owner, "table_name": table_name},
                    )
                    synonym_columns = cursor.fetchall()
                    if synonym_columns:
                        found[synonym_name] = "SYNONYM"
                        column_rows.extend(
                            (synonym_name, *row) for row in synonym_columns
                        )
        objects: dict[str, dict[str, Any]] = {}
        for name, kind in found.items():
            definition, truncated = clip_sql(view_text.get(name))
            objects[name] = {
                "schema": settings.kstl_schema,
                "name": name,
                "kind": kind,
                "synonym_for": (
                    ".".join(synonyms[name]) if name in synonyms else None
                ),
                "columns": [],
                "primary_key": [],
                "unique": [],
                "foreign_keys": [],
                "definition": definition,
                "definition_truncated": truncated,
            }
        for table, position, column, data_type, length, precision, scale, nullable, default in column_rows:
            if table not in objects:
                continue
            objects[table]["columns"].append(
                {
                    "position": position,
                    "name": column,
                    "data_type": oracle_type(str(data_type), length, precision, scale),
                    "nullable": nullable == "Y",
                    "default": None if default is None else scrub(str(default))[:500],
                }
            )
        fk_groups: dict[tuple[str, str], dict[str, Any]] = {}
        unique_groups: dict[tuple[str, str], list[tuple[Any, str]]] = defaultdict(list)
        for table, constraint_type, constraint_name, position, column, ref_table, ref_column in key_rows:
            if table not in objects:
                continue
            if constraint_type == "P":
                objects[table]["primary_key"].append((position, column))
            elif constraint_type == "U":
                unique_groups[(table, constraint_name)].append((position, column))
            else:
                group = fk_groups.setdefault(
                    (table, constraint_name),
                    {
                        "name": constraint_name,
                        "columns": [],
                        "references": {"schema": settings.kstl_schema, "table": ref_table, "columns": []},
                    },
                )
                group["columns"].append((position, column))
                group["references"]["columns"].append((position, ref_column))
        for item in objects.values():
            item["primary_key"] = [column for _, column in sorted(item["primary_key"], key=lambda pair: (pair[0] is None, pair[0]))]
        for (table, _), pairs in unique_groups.items():
            objects[table]["unique"].append(
                [column for _, column in sorted(pairs, key=lambda pair: (pair[0] is None, pair[0]))]
            )
        for (table, _), group in fk_groups.items():
            group["columns"] = [column for _, column in sorted(group["columns"], key=lambda pair: (pair[0] is None, pair[0]))]
            group["references"]["columns"] = [
                column for _, column in sorted(group["references"]["columns"], key=lambda pair: (pair[0] is None, pair[0]))
            ]
            objects[table]["foreign_keys"].append(group)
        result["ok"] = True
        result["objects"] = [objects[name] for name in sorted(objects)]
        result["missing"] = [name for name in names if name not in objects]
        if result["missing"]:
            notes.append("Oracle has no object named: " + ", ".join(result["missing"]))
    except Exception as exc:
        result["error"] = safe_error(exc)
        notes.append("Oracle was not read. " + result["error"])
    return result


def harvest_nifi(notes: list[str]) -> dict[str, Any]:
    paths = sorted(ROOT.glob("NiFi_Flow.json")) + sorted(ROOT.glob("PG_STG_*.json"))
    statements: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            files.append({"file": path.name, "bytes": path.stat().st_size, "error": safe_error(exc)})
            continue
        before = len(statements)
        collect_processors(payload, [], statements)
        if len(statements) == before:
            collect_sql_strings(payload, path.name, statements)
        files.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "statements": len(statements) - before,
            }
        )
    if not paths:
        notes.append(
            "No NiFi_Flow.json or PG_STG_*.json was in the project folder. "
            "Database objects are included. Processor SQL is included only when one of those files is present."
        )
    return {"files": files, "statements": statements}


def collect_processors(node: Any, groups: list[str], statements: list[dict[str, Any]]) -> None:
    if isinstance(node, list):
        for item in node:
            collect_processors(item, groups, statements)
        return
    if not isinstance(node, dict):
        return
    flow = node.get("flowContents")
    if isinstance(flow, dict):
        collect_processors(flow, groups, statements)
        return
    group_name = node.get("name") if "processors" in node or "processGroups" in node else None
    stack = groups + ([str(group_name)] if group_name else [])
    for processor in node.get("processors") or []:
        if not isinstance(processor, dict):
            continue
        properties = processor.get("properties") or {}
        if not isinstance(properties, dict):
            continue
        for key, value in properties.items():
            if not isinstance(value, str) or SECRET_KEY_RE.search(str(key)) or not SQL_RE.search(value):
                continue
            text, truncated = clip_sql(value)
            statements.append(
                {
                    "group": " / ".join(stack),
                    "processor": processor.get("name"),
                    "type": str(processor.get("type") or "").rsplit(".", 1)[-1],
                    "property": key,
                    "sql": text,
                    "sql_truncated": truncated,
                }
            )
    for child in node.get("processGroups") or []:
        collect_processors(child, stack, statements)


def collect_sql_strings(node: Any, label: str, statements: list[dict[str, Any]]) -> None:
    found = 0

    def walk(value: Any, path: list[str]) -> None:
        nonlocal found
        if found >= 300:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if SECRET_KEY_RE.search(str(key)):
                    continue
                walk(item, path + [str(key)])
        elif isinstance(value, list):
            for item in value:
                walk(item, path)
        elif isinstance(value, str) and len(value) > 40 and SQL_RE.search(value):
            text, truncated = clip_sql(value)
            statements.append(
                {
                    "group": label,
                    "processor": " / ".join(path[-6:]),
                    "type": "embedded-sql",
                    "property": path[-1] if path else label,
                    "sql": text,
                    "sql_truncated": truncated,
                }
            )
            found += 1

    walk(node, [])


def gap_notes(payload: dict[str, Any], notes: list[str]) -> None:
    located = {
        str(item.get("name", "")).lower()
        for item in (payload.get("oracle") or {}).get("objects") or []
    }
    missing = [name for name in SOURCE_NAMES if name not in located]
    if missing:
        notes.append("No Oracle column list was found for: " + ", ".join(missing))
    if not (payload.get("nifi") or {}).get("statements"):
        notes.append(
            "No NiFi SQL was found. Oracle column lists are enough to create the raw copies. "
            "Dimension and fact rules need NiFi_Flow.json in this folder."
        )


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    notes: list[str] = []
    settings = get_settings()
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sql_files": sorted(path.name for path in (ROOT / "sql_transformation").glob("*.sql")),
        "source_names": list(SOURCE_NAMES),
        "postgres": probe_postgres(settings, notes),
        "oracle": probe_oracle(settings, notes),
        "nifi": harvest_nifi(notes),
        "notes": notes,
    }
    gap_notes(payload, notes)
    destination = ROOT / "schema-snapshot.json"
    destination.write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wrote {destination}")
    print(f"bytes {destination.stat().st_size}")
    for label in ("postgres", "oracle"):
        item = payload[label]
        print(f"{label} {'ok' if item.get('ok') else 'FAIL'} objects {len(item.get('objects') or [])}")
    print(f"nifi statements {len(payload['nifi']['statements'])}")
    for note in notes:
        print("note:", note)


if __name__ == "__main__":
    main()
