-- Scheme versions opened from prd_scheme in the window.

CREATE TABLE IF NOT EXISTS reportingdw.dim_scheme (
    scheme_sk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schemeid text,
    schemedescription text,
    schemetype text,
    status text,
    start_dt date,
    end_dt date
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_scheme_schemeid_start_dt_idx
    ON reportingdw.dim_scheme (schemeid, start_dt);

INSERT INTO reportingdw.dim_scheme (
    schemeid,
    schemedescription,
    schemetype,
    status,
    start_dt,
    end_dt
)
SELECT
    schemeid::text,
    schemedescription::text,
    schemetype::text,
    status::text,
    makedate::date,
    DATE '9999-12-31'
FROM reportingdw.stg_prd_scheme
WHERE makedate::date BETWEEN current_setting('etl.start_dt')::date
    AND current_setting('etl.end_dt')::date
  AND NOT EXISTS (
      SELECT 1
      FROM reportingdw.dim_scheme AS existing
      WHERE existing.schemeid = stg_prd_scheme.schemeid::text
        AND existing.start_dt = stg_prd_scheme.makedate::date
  );

WITH open_rows AS (
    SELECT
        scheme_sk,
        (
            LEAD(start_dt) OVER (PARTITION BY schemeid ORDER BY start_dt)
            - INTERVAL '1 day'
        )::date AS new_end
    FROM reportingdw.dim_scheme
    WHERE end_dt = DATE '9999-12-31'
)
UPDATE reportingdw.dim_scheme AS dim
SET end_dt = open_rows.new_end
FROM open_rows
WHERE dim.scheme_sk = open_rows.scheme_sk
  AND open_rows.new_end IS NOT NULL;
