from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, model_validator

from app.db import connect
from app.etl.lock import release, try_acquire
from app.etl.runs import create_run, get_run, list_runs
from app.etl.service import run_extract, run_load, run_transform
from app.jobs.catalog import get_extract_job, list_jobs
from app.logging_setup import daily_log_file, safe_db_error

router = APIRouter()


class WindowRequest(BaseModel):
    start_dt: date
    end_dt: date

    @model_validator(mode="after")
    def window_is_ordered(self) -> "WindowRequest":
        if self.end_dt < self.start_dt:
            raise ValueError("end_dt must be on or after start_dt")
        return self


class ExtractRequest(WindowRequest):
    job: str = Field(min_length=1)


class TransformRequest(WindowRequest):
    layer: Literal["staging", "dimension", "fact"]


class AcceptedRun(BaseModel):
    run_id: UUID
    status: str
    pipeline: str


@router.get("/health")
def health() -> dict[str, str]:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=safe_db_error(exc)) from exc
    return {"status": "ok"}


@router.get("/jobs")
def jobs() -> dict[str, list[dict[str, object]]]:
    return {"jobs": list_jobs()}


@router.post("/jobs/load", status_code=202, response_model=AcceptedRun)
def post_load(body: WindowRequest, background_tasks: BackgroundTasks) -> AcceptedRun:
    return _accept(
        background_tasks,
        pipeline="load",
        job="load",
        start_dt=body.start_dt,
        end_dt=body.end_dt,
        worker=run_load,
        worker_args=(body.start_dt, body.end_dt),
    )


@router.post("/jobs/extract", status_code=202, response_model=AcceptedRun)
def post_extract(body: ExtractRequest, background_tasks: BackgroundTasks) -> AcceptedRun:
    job = get_extract_job(body.job)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown extract job: {body.job}")
    if not job.enabled:
        raise HTTPException(status_code=409, detail=f"Extract job is not enabled: {body.job}")
    return _accept(
        background_tasks,
        pipeline="extract",
        job=body.job,
        start_dt=body.start_dt,
        end_dt=body.end_dt,
        worker=run_extract,
        worker_args=(body.job, body.start_dt, body.end_dt),
    )


@router.post("/jobs/transform", status_code=202, response_model=AcceptedRun)
def post_transform(body: TransformRequest, background_tasks: BackgroundTasks) -> AcceptedRun:
    return _accept(
        background_tasks,
        pipeline="transform",
        job=body.layer,
        start_dt=body.start_dt,
        end_dt=body.end_dt,
        worker=run_transform,
        worker_args=(body.layer, body.start_dt, body.end_dt),
    )


@router.get("/runs")
def runs(day: date | None = Query(default=None, alias="date")) -> dict[str, list[dict]]:
    try:
        return {"runs": list_runs(day)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=safe_db_error(exc)) from exc


@router.get("/runs/{run_id}")
def run_detail(run_id: UUID) -> dict:
    try:
        run = get_run(run_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=safe_db_error(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    return run


@router.get("/logs/daily", response_class=PlainTextResponse)
def daily_log(day: date | None = Query(default=None, alias="date")) -> str:
    path = daily_log_file(day)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No log file for {selected.isoformat()}")
    return path.read_text(encoding="utf-8")


def _accept(
    background_tasks: BackgroundTasks,
    pipeline: str,
    job: str | None,
    start_dt: date,
    end_dt: date,
    worker,
    worker_args: tuple,
) -> AcceptedRun:
    if not try_acquire():
        raise HTTPException(status_code=409, detail="Another ETL job is already running")
    try:
        run_id = create_run(pipeline, job, start_dt, end_dt)
        background_tasks.add_task(worker, run_id, *worker_args)
    except Exception:
        release()
        raise
    return AcceptedRun(run_id=run_id, status="queued", pipeline=pipeline)
