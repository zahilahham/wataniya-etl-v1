-- Sales targets for the first of each source month. Open employee rows supply the keys.

CREATE TABLE IF NOT EXISTS reportingdw.fact_emp_target (
    employee_sk bigint,
    manager_sk bigint,
    branch_name text,
    target_date date,
    target_amount numeric
);

CREATE UNIQUE INDEX IF NOT EXISTS fact_emp_target_key_idx
    ON reportingdw.fact_emp_target (employee_sk, manager_sk, target_date);

UPDATE reportingdw.fact_emp_target AS tgt
SET
    branch_name = src.branch_name,
    target_amount = src.target_amount
FROM (
    SELECT
        dimempsale.employee_sk,
        COALESCE(dimempmngr.employee_sk, 0) AS manager_sk,
        base_qry.branch_name,
        base_qry.target_date,
        base_qry.target_amount
    FROM (
        SELECT
            make_date(yr::int, mnth::int, 1) AS target_date,
            area AS branch_name,
            manager_id,
            empid,
            targets::numeric AS target_amount
        FROM reportingdw.stg_mis_sale_target
    ) AS base_qry
    LEFT JOIN reportingdw.dim_employee AS dimempsale
        ON base_qry.empid::text = dimempsale.employeeid
       AND dimempsale.end_dt = DATE '9999-12-31'
    LEFT JOIN reportingdw.dim_employee AS dimempmngr
        ON base_qry.manager_id::text = dimempmngr.employeeid
       AND dimempmngr.end_dt = DATE '9999-12-31'
) AS src
WHERE tgt.employee_sk = src.employee_sk
  AND tgt.manager_sk = src.manager_sk
  AND tgt.target_date = src.target_date
  AND (
      tgt.target_amount IS DISTINCT FROM src.target_amount
      OR tgt.branch_name IS DISTINCT FROM src.branch_name
  );

INSERT INTO reportingdw.fact_emp_target (
    employee_sk,
    manager_sk,
    branch_name,
    target_date,
    target_amount
)
SELECT
    src.employee_sk,
    src.manager_sk,
    src.branch_name,
    src.target_date,
    src.target_amount
FROM (
    SELECT
        dimempsale.employee_sk,
        COALESCE(dimempmngr.employee_sk, 0) AS manager_sk,
        base_qry.branch_name,
        base_qry.target_date,
        base_qry.target_amount
    FROM (
        SELECT
            make_date(yr::int, mnth::int, 1) AS target_date,
            area AS branch_name,
            manager_id,
            empid,
            targets::numeric AS target_amount
        FROM reportingdw.stg_mis_sale_target
    ) AS base_qry
    LEFT JOIN reportingdw.dim_employee AS dimempsale
        ON base_qry.empid::text = dimempsale.employeeid
       AND dimempsale.end_dt = DATE '9999-12-31'
    LEFT JOIN reportingdw.dim_employee AS dimempmngr
        ON base_qry.manager_id::text = dimempmngr.employeeid
       AND dimempmngr.end_dt = DATE '9999-12-31'
) AS src
WHERE NOT EXISTS (
    SELECT 1
    FROM reportingdw.fact_emp_target AS tgt
    WHERE tgt.employee_sk = src.employee_sk
      AND tgt.manager_sk = src.manager_sk
      AND tgt.target_date = src.target_date
);
