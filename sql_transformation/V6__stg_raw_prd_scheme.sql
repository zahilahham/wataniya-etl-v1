-- Copy raw.prd_scheme into reportingdw.stg_prd_scheme.

CREATE TABLE IF NOT EXISTS reportingdw.stg_prd_scheme (LIKE raw.prd_scheme INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_prd_scheme;

INSERT INTO reportingdw.stg_prd_scheme
SELECT *
FROM raw.prd_scheme;
