-- Copy raw.ext_simah_rpt_header into reportingdw.stg_ext_simah_rpt_header.

CREATE TABLE IF NOT EXISTS reportingdw.stg_ext_simah_rpt_header (LIKE raw.ext_simah_rpt_header INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_ext_simah_rpt_header;

INSERT INTO reportingdw.stg_ext_simah_rpt_header
SELECT *
FROM raw.ext_simah_rpt_header;
