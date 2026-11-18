-- Copy raw.cif_address into reportingdw.stg_cif_address.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_address (LIKE raw.cif_address INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_address;

INSERT INTO reportingdw.stg_cif_address
SELECT *
FROM raw.cif_address;
