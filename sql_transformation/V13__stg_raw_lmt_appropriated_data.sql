-- Copy raw.lmt_appropriated_data into reportingdw.stg_lmt_appropriated_data.

CREATE TABLE IF NOT EXISTS reportingdw.stg_lmt_appropriated_data (LIKE raw.lmt_appropriated_data INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_lmt_appropriated_data;

INSERT INTO reportingdw.stg_lmt_appropriated_data
SELECT *
FROM raw.lmt_appropriated_data;
