-- Copy raw.lct_daily_coll_status into reportingdw.stg_lct_daily_coll_status.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lct_daily_coll_status (LIKE raw.lct_daily_coll_status INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lct_daily_coll_status;

INSERT INTO reportingdw.stg_lct_daily_coll_status
SELECT *
FROM raw.lct_daily_coll_status;
