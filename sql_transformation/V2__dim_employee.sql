-- Build the open-ended employee dimension from reportingdw.stg_employee.
-- etl.start_dt and etl.end_dt are set by the Python runner for this session.

CREATE TABLE IF NOT EXISTS reportingdw.dim_employee (
    employee_sk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employeeid text,
    employeecode text,
    employeename text,
    status text,
    cg_locationcode text,
    start_dt date,
    end_dt date
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_employee_employeeid_start_dt_idx
    ON reportingdw.dim_employee (employeeid, start_dt);

INSERT INTO reportingdw.dim_employee (
    employeeid,
    employeecode,
    employeename,
    status,
    cg_locationcode,
    start_dt,
    end_dt
)
SELECT
    latest.employeeid::text,
    latest.employeecode::text,
    latest.employeename::text,
    latest.status::text,
    latest.cg_locationcode::text,
    latest.makedate::date,
    DATE '9999-12-31'
FROM (
    SELECT
        employeeid,
        employeecode,
        employeename,
        status,
        cg_locationcode,
        makedate,
        ROW_NUMBER() OVER (
            PARTITION BY employeeid
            ORDER BY makedate DESC
        ) AS rn
    FROM reportingdw.stg_employee
    WHERE makedate::date BETWEEN current_setting('etl.start_dt')::date
        AND current_setting('etl.end_dt')::date
) AS latest
WHERE latest.rn = 1
  AND NOT EXISTS (
      SELECT 1
      FROM reportingdw.dim_employee AS existing
      WHERE existing.employeeid = latest.employeeid::text
        AND existing.start_dt = latest.makedate::date
  );

WITH open_rows AS (
    SELECT
        employee_sk,
        (
            LEAD(start_dt) OVER (
                PARTITION BY employeeid
                ORDER BY start_dt
            ) - INTERVAL '1 day'
        )::date AS new_end
    FROM reportingdw.dim_employee
    WHERE end_dt = DATE '9999-12-31'
)
UPDATE reportingdw.dim_employee AS dim
SET end_dt = open_rows.new_end
FROM open_rows
WHERE dim.employee_sk = open_rows.employee_sk
  AND open_rows.new_end IS NOT NULL;
