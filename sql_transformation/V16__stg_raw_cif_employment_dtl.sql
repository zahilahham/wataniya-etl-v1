-- Copy raw.cif_employment_dtl into reportingdw.stg_cif_employment_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_employment_dtl (LIKE raw.cif_employment_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_employment_dtl;

INSERT INTO reportingdw.stg_cif_employment_dtl
SELECT *
FROM raw.cif_employment_dtl;
