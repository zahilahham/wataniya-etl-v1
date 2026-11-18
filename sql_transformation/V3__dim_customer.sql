-- Latest customer attributes in the window, one open version per change date.
-- etl.start_dt and etl.end_dt are set by the Python runner for this session.

CREATE TABLE IF NOT EXISTS reportingdw.dim_customer (
    customer_sk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customercif_id text,
    customername text,
    nationality text,
    sex text,
    idnumber text,
    mobile text,
    birth_date timestamp,
    sgment text,
    total_income numeric,
    net_income numeric,
    employername text,
    service_years numeric,
    cg_sector_economy text,
    cg_designation text,
    start_dt date,
    end_dt date
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_customer_cif_start_dt_idx
    ON reportingdw.dim_customer (customercif_id, start_dt);

INSERT INTO reportingdw.dim_customer (
    customercif_id,
    customername,
    nationality,
    sex,
    idnumber,
    mobile,
    birth_date,
    sgment,
    total_income,
    net_income,
    employername,
    service_years,
    cg_sector_economy,
    cg_designation,
    start_dt,
    end_dt
)
SELECT
    base.cifid::text,
    base.customername::text,
    cg_ntion.description::text,
    base.sex::text,
    idnd.idnumber::text,
    addr.mobile::text,
    base.dobdoi,
    base.indvcorpflag::text,
    cch.total_income,
    cch.net_income,
    empd.employername::text,
    empd.service_years,
    empd.cg_sector_economy::text,
    empd.cg_designation::text,
    cal.cal_date,
    DATE '9999-12-31'
FROM generate_series(
    current_setting('etl.start_dt')::date,
    current_setting('etl.end_dt')::date,
    INTERVAL '1 day'
) AS cal(cal_date)
LEFT JOIN (
    SELECT
        cifid,
        customername,
        cg_nationalityid,
        sex,
        dobdoi,
        indvcorpflag,
        makedate::date AS makedate
    FROM reportingdw.stg_cif_customer
    WHERE makedate::date BETWEEN current_setting('etl.start_dt')::date
        AND current_setting('etl.end_dt')::date
) AS base
    ON cal.cal_date >= base.makedate
LEFT JOIN (
    SELECT
        cifid,
        total_income,
        net_income,
        makedate AS start_dt,
        COALESCE(
            (
                LEAD(makedate) OVER (PARTITION BY cifid ORDER BY makedate)
                - INTERVAL '1 day'
            )::date,
            DATE '9999-12-31'
        ) AS end_dt
    FROM (
        SELECT
            cifid,
            total_income,
            net_income,
            makedate::date AS makedate
        FROM reportingdw.stg_cif_custincomebreakup_hdr
    ) AS income
) AS cch
    ON cch.cifid = base.cifid
   AND cch.start_dt >= base.makedate
   AND cal.cal_date BETWEEN cch.start_dt AND cch.end_dt
LEFT JOIN (
    SELECT
        cifid,
        employername,
        yearsatcurrempl AS service_years,
        cg_sector_economy,
        cg_designation,
        makedate AS start_dt,
        COALESCE(
            (
                LEAD(makedate) OVER (PARTITION BY cifid ORDER BY makedate)
                - INTERVAL '1 day'
            )::date,
            DATE '9999-12-31'
        ) AS end_dt
    FROM (
        SELECT DISTINCT
            cifid,
            employername,
            yearsatcurrempl,
            cg_sector_economy,
            cg_designation,
            makedate::date AS makedate
        FROM reportingdw.stg_cif_employment_dtl
    ) AS employment
) AS empd
    ON empd.cifid = base.cifid
   AND empd.start_dt >= base.makedate
   AND cal.cal_date BETWEEN empd.start_dt AND empd.end_dt
LEFT JOIN (
    SELECT cifid, mobile1 AS mobile
    FROM (
        SELECT
            cifid,
            mobile1,
            ROW_NUMBER() OVER (PARTITION BY cifid ORDER BY makedate DESC) AS rn
        FROM reportingdw.stg_cif_address
    ) AS address
    WHERE rn = 1
) AS addr
    ON addr.cifid = base.cifid
LEFT JOIN (
    SELECT cifid, idnumber
    FROM (
        SELECT
            cifid,
            idnumber,
            ROW_NUMBER() OVER (PARTITION BY cifid ORDER BY makedate DESC) AS rn
        FROM reportingdw.stg_cif_identification_details
    ) AS identification
    WHERE rn = 1
) AS idnd
    ON idnd.cifid = base.cifid
LEFT JOIN reportingdw.stg_company_generic AS cg_ntion
    ON cg_ntion.genericid = base.cg_nationalityid
WHERE base.cifid IS NOT NULL
  AND (cal.cal_date = base.makedate OR cal.cal_date = cch.start_dt)
  AND NOT EXISTS (
      SELECT 1
      FROM reportingdw.dim_customer AS existing
      WHERE existing.customercif_id = base.cifid::text
        AND existing.start_dt = cal.cal_date
  );

WITH open_rows AS (
    SELECT
        customer_sk,
        (
            LEAD(start_dt) OVER (PARTITION BY customercif_id ORDER BY start_dt)
            - INTERVAL '1 day'
        )::date AS new_end
    FROM reportingdw.dim_customer
    WHERE end_dt = DATE '9999-12-31'
)
UPDATE reportingdw.dim_customer AS dim
SET end_dt = open_rows.new_end
FROM open_rows
WHERE dim.customer_sk = open_rows.customer_sk
  AND open_rows.new_end IS NOT NULL;
