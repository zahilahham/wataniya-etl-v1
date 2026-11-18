-- Copy raw.cif_customer into reportingdw.stg_cif_customer.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_customer (LIKE raw.cif_customer INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_customer;

INSERT INTO reportingdw.stg_cif_customer
SELECT *
FROM raw.cif_customer;
