-- Copy raw.product into reportingdw.stg_product.

CREATE TABLE IF NOT EXISTS reportingdw.stg_product (LIKE raw.product INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_product;

INSERT INTO reportingdw.stg_product
SELECT *
FROM raw.product;
