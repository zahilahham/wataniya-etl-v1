-- Copy raw.collection_target into reportingdw.stg_collection_target.

CREATE TABLE IF NOT EXISTS reportingdw.stg_collection_target (LIKE raw.collection_target INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_collection_target;

INSERT INTO reportingdw.stg_collection_target
SELECT *
FROM raw.collection_target;
