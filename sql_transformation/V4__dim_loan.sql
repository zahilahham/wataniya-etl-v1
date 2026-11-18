-- Open loan version from the latest loan detail in the window.

CREATE TABLE IF NOT EXISTS reportingdw.dim_loan (
    loan_sk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    loanid text,
    loanno text,
    cifid text,
    appid text,
    productcode text,
    loanamount numeric,
    interest_rate numeric,
    tenure numeric,
    emi numeric,
    cg_repay_freq text,
    inst_start_dt timestamp,
    inst_end_dt timestamp,
    disbursal_date timestamp,
    cg_loan_status text,
    remidial_flag text,
    start_dt date,
    end_dt date
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_loan_loanid_start_dt_idx
    ON reportingdw.dim_loan (loanid, start_dt);

INSERT INTO reportingdw.dim_loan (
    loanid,
    loanno,
    cifid,
    appid,
    productcode,
    loanamount,
    interest_rate,
    tenure,
    emi,
    cg_repay_freq,
    inst_start_dt,
    inst_end_dt,
    disbursal_date,
    cg_loan_status,
    remidial_flag,
    start_dt,
    end_dt
)
SELECT
    base.loanid::text,
    base.loanno::text,
    base.cifid::text,
    base.srcapplid::text,
    base.productcode::text,
    base.loanamount,
    lpd.rate,
    base.tenure,
    base.emi,
    base.cg_repay_freq::text,
    base.inst_start_dt,
    base.inst_end_dt,
    base.disbursal_date,
    base.cg_loan_status::text,
    lcld.remidial_flag::text,
    base.makedate::date,
    DATE '9999-12-31'
FROM reportingdw.stg_lmt_loan_dtl AS base
LEFT JOIN reportingdw.stg_lot_globalloan_t AS lgt
    ON lgt.comp_appl_id = base.srcapplid
LEFT JOIN reportingdw.stg_lct_loan_dtl AS lcld
    ON lcld.loanid = base.loanid
LEFT JOIN (
    SELECT
        comp_appl_id,
        rate,
        ROW_NUMBER() OVER (PARTITION BY comp_appl_id ORDER BY makedate DESC) AS rn
    FROM reportingdw.stg_lot_penaltyinterestrate_dtl
    WHERE makedate::date BETWEEN current_setting('etl.start_dt')::date
        AND current_setting('etl.end_dt')::date
) AS lpd
    ON lpd.comp_appl_id = lgt.comp_appl_id
   AND lpd.rn = 1
WHERE base.makedate::date BETWEEN current_setting('etl.start_dt')::date
    AND current_setting('etl.end_dt')::date
  AND NOT EXISTS (
      SELECT 1
      FROM reportingdw.dim_loan AS existing
      WHERE existing.loanid = base.loanid::text
        AND existing.start_dt = base.makedate::date
  );

WITH open_rows AS (
    SELECT
        loan_sk,
        (
            LEAD(start_dt) OVER (PARTITION BY loanid ORDER BY start_dt)
            - INTERVAL '1 day'
        )::date AS new_end
    FROM reportingdw.dim_loan
    WHERE end_dt = DATE '9999-12-31'
)
UPDATE reportingdw.dim_loan AS dim
SET end_dt = open_rows.new_end
FROM open_rows
WHERE dim.loan_sk = open_rows.loan_sk
  AND open_rows.new_end IS NOT NULL;
