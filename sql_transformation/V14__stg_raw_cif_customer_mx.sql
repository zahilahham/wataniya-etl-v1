-- Copy raw.cif_customer_mx into reportingdw.stg_cif_customer_mx.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_customer_mx (LIKE raw.cif_customer_mx INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_customer_mx;

INSERT INTO reportingdw.stg_cif_customer_mx
SELECT *
FROM raw.cif_customer_mx;
