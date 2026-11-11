from datetime import date
from uuid import UUID

from app.config import get_settings
from app.db import connect
from app.etl.extract_load import extract_employee
from app.etl.lock import release
from app.etl.transform import execute_sql_transformations
from app.logging_setup import RunLog, redact


def run_extract(run_id: UUID, job: str, start_dt: date, end_dt: date) -> None:
    log: RunLog | None = None
    try:
        log = RunLog(run_id)
        log.set_status("running")
        log.event(
            "INFO",
            "extract",
            f"Extract started for {job} window {start_dt.isoformat()} to {end_dt.isoformat()}",
        )
        if job != "employee":
            raise RuntimeError(f"No extract implementation for {job}")
        with connect() as conn:
            loaded = extract_employee(conn, log, start_dt, end_dt, get_settings())
            conn.commit()
        log.set_status("success")
        log.event(
            "INFO",
            "extract",
            f"Extract finished for {job}",
            rows=loaded,
        )
    except Exception as exc:
        if log is None:
            _mark_failed_without_log(run_id, exc)
        else:
            _fail(log, "extract", exc)
    finally:
        if log is not None:
            log.close()
        release()


def run_transform(run_id: UUID, layer: str, start_dt: date, end_dt: date) -> None:
    log: RunLog | None = None
    try:
        log = RunLog(run_id)
        log.set_status("running")
        log.event(
            "INFO",
            "transform",
            f"Transform started for {layer} window {start_dt.isoformat()} to {end_dt.isoformat()}",
        )
        settings = get_settings()
        with connect() as conn:
            execute_sql_transformations(conn, log, start_dt, end_dt, settings.sql_dir, layer)
            conn.commit()
        log.set_status("success")
        log.event("INFO", "transform", f"Transform finished for {layer}")
    except Exception as exc:
        if log is None:
            _mark_failed_without_log(run_id, exc)
        else:
            _fail(log, "transform", exc)
    finally:
        if log is not None:
            log.close()
        release()


def _fail(log: RunLog, step: str, exc: Exception) -> None:
    message = redact(str(exc))
    try:
        log.set_status("failed", error=message)
        log.event("ERROR", step, f"{step} failed: {message}")
    except Exception:
        return


def _mark_failed_without_log(run_id: UUID, exc: Exception) -> None:
    message = redact(str(exc))
    try:
        with connect() as conn:
            conn.execute(
                """
                UPDATE etl.run
                SET status = 'failed', finished_at = now(), error = %s
                WHERE run_id = %s
                """,
                (message, run_id),
            )
            conn.commit()
    except Exception:
        return
