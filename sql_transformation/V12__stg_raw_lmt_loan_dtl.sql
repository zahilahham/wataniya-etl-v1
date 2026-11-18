-- Copy raw.lmt_loan_dtl into reportingdw.stg_lmt_loan_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lmt_loan_dtl (LIKE raw.lmt_loan_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lmt_loan_dtl;

INSERT INTO reportingdw.stg_lmt_loan_dtl
SELECT *
FROM raw.lmt_loan_dtl;
