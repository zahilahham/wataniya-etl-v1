-- Copy raw.company_employee_role into reportingdw.stg_company_employee_role.

CREATE TABLE IF NOT EXISTS reportingdw.stg_company_employee_role (LIKE raw.company_employee_role INCLUDING ALL);

TRUNCATE TABLE reportingdw.stg_company_employee_role;

INSERT INTO reportingdw.stg_company_employee_role
SELECT *
FROM raw.company_employee_role;
