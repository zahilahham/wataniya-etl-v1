import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.config import get_settings

DDL_STATEMENTS = (
    "CREATE SCHEMA IF NOT EXISTS raw",
    "CREATE SCHEMA IF NOT EXISTS reportingdw",
    "CREATE SCHEMA IF NOT EXISTS etl",
    """
    CREATE TABLE IF NOT EXISTS etl.run (
        run_id uuid PRIMARY KEY,
        pipeline text NOT NULL,
        job text,
        status text NOT NULL,
        start_dt date,
        end_dt date,
        started_at timestamptz,
        finished_at timestamptz,
        error text,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS etl.run_event (
        event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        run_id uuid NOT NULL REFERENCES etl.run (run_id),
        logged_at timestamptz NOT NULL DEFAULT now(),
        level text NOT NULL,
        step text NOT NULL,
        message text NOT NULL,
        rows integer,
        duration_ms integer,
        sql_file text
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS run_event_run_id_idx
        ON etl.run_event (run_id, event_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS run_created_at_idx
        ON etl.run (created_at DESC)
    """,
)


def connect() -> Connection:
    return psycopg.connect(get_settings().postgres_dsn, row_factory=dict_row)


def init_db() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            for statement in DDL_STATEMENTS:
                cur.execute(statement)
        conn.commit()
