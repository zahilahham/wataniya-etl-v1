-- Copy raw.coll_month_distribution into reportingdw.stg_coll_month_distribution.

CREATE TABLE IF NOT EXISTS reportingdw.stg_coll_month_distribution (LIKE raw.coll_month_distribution INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_coll_month_distribution;

INSERT INTO reportingdw.stg_coll_month_distribution
SELECT *
FROM raw.coll_month_distribution;
