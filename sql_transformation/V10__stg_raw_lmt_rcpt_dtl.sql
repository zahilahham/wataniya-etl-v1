-- Copy raw.lmt_rcpt_dtl into reportingdw.stg_lmt_rcpt_dtl.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lmt_rcpt_dtl (LIKE raw.lmt_rcpt_dtl INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lmt_rcpt_dtl;

INSERT INTO reportingdw.stg_lmt_rcpt_dtl
SELECT *
FROM raw.lmt_rcpt_dtl;
