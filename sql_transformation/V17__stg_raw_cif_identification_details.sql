-- Copy raw.cif_identification_details into reportingdw.stg_cif_identification_details.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_identification_details (LIKE raw.cif_identification_details INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_identification_details;

INSERT INTO reportingdw.stg_cif_identification_details
SELECT *
FROM raw.cif_identification_details;
