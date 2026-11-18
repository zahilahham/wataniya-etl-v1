-- Copy raw.lot_globalloan_t into reportingdw.stg_lot_globalloan_t.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lot_globalloan_t (LIKE raw.lot_globalloan_t INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lot_globalloan_t;

INSERT INTO reportingdw.stg_lot_globalloan_t
SELECT *
FROM raw.lot_globalloan_t;
