-- Copy raw.mis_sale_target into reportingdw.stg_mis_sale_target.

CREATE TABLE IF NOT EXISTS reportingdw.stg_mis_sale_target (LIKE raw.mis_sale_target INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_mis_sale_target;

INSERT INTO reportingdw.stg_mis_sale_target
SELECT *
FROM raw.mis_sale_target;
