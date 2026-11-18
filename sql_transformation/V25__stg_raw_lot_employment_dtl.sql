-- Copy raw.lot_employment_dtl into reportingdw.stg_lot_employment_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lot_employment_dtl (LIKE raw.lot_employment_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lot_employment_dtl;

INSERT INTO reportingdw.stg_lot_employment_dtl
SELECT *
FROM raw.lot_employment_dtl;
