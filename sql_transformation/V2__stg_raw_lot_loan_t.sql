-- Copy raw.lot_loan_t into reportingdw.stg_lot_loan_t.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lot_loan_t (LIKE raw.lot_loan_t INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lot_loan_t;

INSERT INTO reportingdw.stg_lot_loan_t
SELECT *
FROM raw.lot_loan_t;
