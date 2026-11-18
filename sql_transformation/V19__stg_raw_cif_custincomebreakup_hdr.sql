-- Copy raw.cif_custincomebreakup_hdr into reportingdw.stg_cif_custincomebreakup_hdr.

CREATE TABLE IF NOT EXISTS reportingdw.stg_cif_custincomebreakup_hdr (LIKE raw.cif_custincomebreakup_hdr INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_cif_custincomebreakup_hdr;

INSERT INTO reportingdw.stg_cif_custincomebreakup_hdr
SELECT *
FROM raw.cif_custincomebreakup_hdr;
