-- Copy raw.employee into reportingdw.stg_employee.

CREATE TABLE IF NOT EXISTS reportingdw.stg_employee (LIKE raw.employee INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_employee;

INSERT INTO reportingdw.stg_employee
SELECT *
FROM raw.employee;
