-- Copy raw.lot_penaltyinterestrate_dtl into reportingdw.stg_lot_penaltyinterestrate_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lot_penaltyinterestrate_dtl (LIKE raw.lot_penaltyinterestrate_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lot_penaltyinterestrate_dtl;

INSERT INTO reportingdw.stg_lot_penaltyinterestrate_dtl
SELECT *
FROM raw.lot_penaltyinterestrate_dtl;
