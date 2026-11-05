# Wataniya ETL

On-demand extract and SQL transform. Python loads one Oracle table into PostgreSQL unchanged. A single function then runs versioned SQL files in folder order and writes the reporting tables.

`EMPLOYEE` is the only live extract. The other folders under `sql_transformation/` are placeholders.

## What a run does

1. `POST /jobs/extract` reads `PULSE_NFC_PROD.EMPLOYEE` for a date window and loads it into `raw.employee`.
2. `POST /jobs/transform` runs `sql_transformation/*/V1__transformation_job.sql` in folder-name order.
3. The employee script fills `reportingdw.stg_employee` and `reportingdw.dim_employee`.

Startup creates the `raw`, `reportingdw`, and `etl` schemas. Each step is written to `logs/etl-YYYY-MM-DD.log` and to `etl.run_event`.

## What you need

- Python 3.10 or newer
- A PostgreSQL database you can create schemas in
- Oracle network access to Kastle, plus a user that can read `EMPLOYEE`
- The Oracle schema name. The default is `PULSE_NFC_PROD`

## Setup

From this directory:

```text
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, create the virtualenv with `python3 -m venv .venv` and activate it with `source .venv/bin/activate`.

Create the database, then edit `.env`:

```text
POSTGRES_DSN=postgresql://USER:PASSWORD@HOST:5432/wataniya
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_DSN=host:1521/service_name
KSTL_SCHEMA=PULSE_NFC_PROD
```

`ORACLE_DSN` is the host, port, and service name. Do not commit `.env`.

Example, if the local Postgres user is `postgres`:

```text
psql -U postgres -c "CREATE DATABASE wataniya;"
```

## Start the API

```text
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Check PostgreSQL:

```text
curl http://127.0.0.1:8000/health
```

`{"status":"ok"}` means the app can query PostgreSQL. A 503 means `POSTGRES_DSN` is wrong or the database is down.

## Run the employee load

Extract first. Replace the dates with the window you want. `MAKEDATE` is inclusive of both dates.

```text
curl -X POST http://127.0.0.1:8000/jobs/extract ^
  -H "Content-Type: application/json" ^
  -d "{\"job\":\"employee\",\"start_dt\":\"2026-06-01\",\"end_dt\":\"2026-06-30\"}"
```

The response is `202` with a `run_id`. Only one extract or transform can run at a time. A second call returns `409`.

Poll until `status` is `success` or `failed`:

```text
curl http://127.0.0.1:8000/runs/RUN_ID
```

The `events` list is the detailed step log: Oracle connect, columns, truncate, each copy batch, and the commit. The same lines are in `logs/etl-YYYY-MM-DD.log`.

```text
curl "http://127.0.0.1:8000/logs/daily?date=2026-11-05"
```

After the extract succeeds, run the SQL transform for the same window:

```text
curl -X POST http://127.0.0.1:8000/jobs/transform ^
  -H "Content-Type: application/json" ^
  -d "{\"start_dt\":\"2026-06-01\",\"end_dt\":\"2026-06-30\"}"
```

Poll that `run_id` the same way. A failed statement stops the SQL sequence. The event message includes the statement preview and the database error.

Confirm the tables:

```text
SELECT COUNT(*) FROM raw.employee;
SELECT COUNT(*) FROM reportingdw.stg_employee;
SELECT COUNT(*) FROM reportingdw.dim_employee;
```

`reportingdw.dim_employee` keeps the latest row per employee in the window, with `end_dt = 9999-12-31`. A later window closes the previous open row to the day before the new `start_dt`.

## Job list

```text
curl http://127.0.0.1:8000/jobs
```

`employee` and `010_employee` are enabled. Every other job is reserved for a later SQL file. The runner ignores a folder until `V1__transformation_job.sql` exists and contains at least one statement.

## Tests

No database is required:

```text
.venv\Scripts\python.exe -m unittest tests.test_sql_transform -v
```
