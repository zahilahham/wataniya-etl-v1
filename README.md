# Wataniya ETL

On-demand extract and SQL transform. Python loads one Oracle table into PostgreSQL unchanged. `sql_transformation/` holds only SQL files. The number is the run order. A load from outside the warehouse is named `V1__stg_raw_employee.sql`. A later step whose source is already in the warehouse is named `V2__dim_employee.sql`.

Every Kastle source in the catalog is a live extract. Staging, dimension, and fact SQL are in `sql_transformation/`.

## What a run does

1. `POST /jobs/extract` reads one Oracle object for a date window and loads it unchanged into `raw.<job>`. `company_generic` stores `KEY` as `key_ms`. `coll_month_distribution`, `mis_sale_target`, and `collection_target` are full copies.
2. `POST /jobs/transform` takes a `layer` of `staging`, `dimension`, or `fact`. The runner splits each file name on `__`, reads the number, and runs that layer's files in that order. `stg_` is staging, `dim_` is dimension, and `fact_` is fact.
3. `staging` copies each `raw` table into `reportingdw`. `dimension` builds employee, customer, loan, scheme, product, and company generic. `fact` builds application, sales target, and monthly collection.

Startup creates the `raw`, `reportingdw`, and `etl` schemas. Each step is written to `logs/etl-YYYY-MM-DD.log` and to `etl.run_event`.

## What you need

- Python 3.10 or newer
- A PostgreSQL database you can create schemas in
- Oracle network access to Kastle, plus a user that can read the `PULSE_NFC_PROD` tables in the catalog
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

Oracle is the only source. PostgreSQL is the data lake: `raw` holds the extract and `reportingdw` holds the staging, dimension, and fact tables. `ORACLE_DSN` is the host, port, and service name from `CS_CONN_DB_KASTLE`, without the `jdbc:oracle:thin:@//` prefix. Do not commit `.env`.

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

## Run a window

One call loads every Oracle source, then staging, dimension, and fact. Replace the dates with the window you want. `MAKEDATE` is inclusive of both dates.

```text
curl -X POST http://127.0.0.1:8000/jobs/load ^
  -H "Content-Type: application/json" ^
  -d "{\"start_dt\":\"2026-06-01\",\"end_dt\":\"2026-06-30\"}"
```

The response is `202` with a `run_id`. Only one load can run at a time. A second call returns `409`. A failed extract or SQL statement stops the load.

Poll until `status` is `success` or `failed`:

```text
curl http://127.0.0.1:8000/runs/RUN_ID
```

The `events` list is the detailed step log: Oracle connect, columns, truncate, each copy batch, and the commit. The same lines are in `logs/etl-YYYY-MM-DD.log`.

```text
curl "http://127.0.0.1:8000/logs/daily?date=2026-11-05"
```

`/jobs/extract` and `/jobs/transform` remain for one source or one layer. The full window is `/jobs/load`.

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

`POST /jobs/load` runs every enabled extract, then staging, dimension, and fact, for one window. Scheme is built before product.

## Tests

No database is required:

```text
.venv\Scripts\python.exe -m unittest tests.test_sql_transform -v
```
