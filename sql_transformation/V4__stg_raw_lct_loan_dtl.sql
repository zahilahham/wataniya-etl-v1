-- Copy raw.lct_loan_dtl into reportingdw.stg_lct_loan_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lct_loan_dtl (LIKE raw.lct_loan_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lct_loan_dtl;

INSERT INTO reportingdw.stg_lct_loan_dtl
SELECT *
FROM raw.lct_loan_dtl;
