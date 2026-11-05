from datetime import date, datetime
from uuid import UUID, uuid4

from app.db import connect


def create_run(
    pipeline: str,
    job: str | None,
    start_dt: date,
    end_dt: date,
) -> UUID:
    run_id = uuid4()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO etl.run (run_id, pipeline, job, status, start_dt, end_dt)
            VALUES (%s, %s, %s, 'queued', %s, %s)
            """,
            (run_id, pipeline, job, start_dt, end_dt),
        )
        conn.commit()
    return run_id


def get_run(run_id: UUID) -> dict | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM etl.run WHERE run_id = %s", (run_id,))
            run = cur.fetchone()
            if run is None:
                return None
            cur.execute(
                """
                SELECT event_id, logged_at, level, step, message, rows, duration_ms, sql_file
                FROM etl.run_event
                WHERE run_id = %s
                ORDER BY event_id
                """,
                (run_id,),
            )
            run["events"] = list(cur.fetchall())
            return run


def list_runs(day: date | None = None, limit: int = 100) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            if day is None:
                cur.execute(
                    """
                    SELECT *
                    FROM etl.run
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                start = datetime.combine(day, datetime.min.time()).astimezone()
                end = datetime.combine(day, datetime.max.time()).astimezone()
                cur.execute(
                    """
                    SELECT *
                    FROM etl.run
                    WHERE created_at >= %s AND created_at <= %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (start, end, limit),
                )
            return list(cur.fetchall())
