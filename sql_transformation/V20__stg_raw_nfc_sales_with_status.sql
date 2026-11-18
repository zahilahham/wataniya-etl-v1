-- Copy raw.nfc_sales_with_status into reportingdw.stg_nfc_sales_with_status.

CREATE TABLE IF NOT EXISTS reportingdw.stg_nfc_sales_with_status (LIKE raw.nfc_sales_with_status INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_nfc_sales_with_status;

INSERT INTO reportingdw.stg_nfc_sales_with_status
SELECT *
FROM raw.nfc_sales_with_status;
