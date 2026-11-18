-- Copy raw.company_generic into reportingdw.stg_company_generic.

CREATE TABLE IF NOT EXISTS reportingdw.stg_company_generic (LIKE raw.company_generic INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_company_generic;

INSERT INTO reportingdw.stg_company_generic
SELECT *
FROM raw.company_generic;
