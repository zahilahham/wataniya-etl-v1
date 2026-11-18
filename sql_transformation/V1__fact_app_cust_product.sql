-- Replace application facts whose snapshot date falls in the window.

CREATE TABLE IF NOT EXISTS reportingdw.fact_app_cust_product (
    appid text,
    app_entry_date timestamp,
    snapshot_dt timestamp,
    customer_sk bigint,
    loan_sk bigint,
    product_type text,
    product_sk bigint,
    employee_sk bigint,
    manager_sk bigint,
    contract_no text,
    approved_date timestamp,
    funded_date timestamp,
    customer_segment text,
    loan_amount numeric,
    funded_amount numeric,
    branch_code text,
    branch_name text,
    salesman_id text,
    salesman text,
    customer_name_ar text,
    customer_name_en text,
    simah_score text,
    customer_designation text,
    sector text,
    contact_no text,
    scheme1 text,
    scheme text,
    profit_rate numeric,
    contract_status text,
    contract_status1 text,
    rejected_stage text,
    rejected_date timestamp,
    rejected_department text,
    rejected_department1 text,
    pending_stage text,
    pending_with text,
    pending_since timestamp,
    pending_department text,
    pending_department1 text,
    app_entry_status text,
    rejection_reason text,
    promotion text,
    application_score text,
    score_range text
);

DELETE FROM reportingdw.fact_app_cust_product AS tgt
USING (
    SELECT base.application_no AS appid
    FROM (
        SELECT
            application_no,
            salesman_id,
            b.productcode,
            application_date,
            COALESCE(
                application_date,
                approved_date,
                funded_date,
                rejected_date,
                pending_since
            ) AS snapshot_dt
        FROM reportingdw.stg_nfc_sales_with_status AS a
        JOIN reportingdw.stg_lot_globalloan_t AS b
            ON b.comp_appl_id = a.application_no
        WHERE COALESCE(
                application_date,
                approved_date,
                funded_date,
                rejected_date,
                pending_since
            )::date BETWEEN current_setting('etl.start_dt')::date
                AND current_setting('etl.end_dt')::date
    ) AS base
    LEFT JOIN (
        SELECT
            cifid,
            comp_appl_id,
            ROW_NUMBER() OVER (PARTITION BY comp_appl_id ORDER BY makedate DESC) AS ordr
        FROM reportingdw.stg_cif_customer_mx
        WHERE cifid IS NOT NULL
          AND comp_appl_id IS NOT NULL
    ) AS ccmx
        ON ccmx.comp_appl_id = base.application_no
       AND ccmx.ordr = 1
    LEFT JOIN reportingdw.stg_cif_customer AS cust
        ON ccmx.cifid = cust.cifid
    LEFT JOIN (
        SELECT
            employeecode,
            supervisorcode,
            productcode,
            makedate AS start_dt,
            COALESCE(
                LEAD(makedate) OVER (
                    PARTITION BY employeecode, productcode
                    ORDER BY makedate
                ),
                TIMESTAMP '9999-12-31'
            ) AS end_dt
        FROM reportingdw.stg_company_employee_role
        WHERE cg_rolecode = 'SLS'
          AND status <> 'X'
    ) AS emp_magr
        ON base.salesman_id = emp_magr.employeecode
       AND base.productcode = emp_magr.productcode
       AND base.application_date BETWEEN emp_magr.start_dt AND emp_magr.end_dt
) AS src
WHERE tgt.appid = src.appid::text;

INSERT INTO reportingdw.fact_app_cust_product (
    appid, app_entry_date, snapshot_dt, customer_sk, loan_sk, product_type, product_sk,
    employee_sk, manager_sk, contract_no, approved_date, funded_date, customer_segment,
    loan_amount, funded_amount, branch_code, branch_name, salesman_id, salesman,
    customer_name_ar, customer_name_en, simah_score, customer_designation, sector,
    contact_no, scheme1, scheme, profit_rate, contract_status, contract_status1,
    rejected_stage, rejected_date, rejected_department, rejected_department1,
    pending_stage, pending_with, pending_since, pending_department, pending_department1,
    app_entry_status, rejection_reason, promotion, application_score, score_range
)
SELECT
    base_qry.appid::text,
    base_qry.app_entry_date,
    base_qry.snapshot_dt,
    dimcust.customer_sk,
    dimln.loan_sk,
    base_qry.product_type::text,
    dimprod.product_sk,
    dimempsale.employee_sk,
    dimempmngr.employee_sk,
    base_qry.contract_no::text,
    base_qry.approved_date,
    base_qry.funded_date,
    base_qry.customer_segment::text,
    base_qry.loan_amount,
    base_qry.funded_amount,
    base_qry.branch_code::text,
    base_qry.branch_name::text,
    base_qry.salesman_id::text,
    base_qry.salesman::text,
    base_qry.customer_name_ar::text,
    base_qry.customer_name_en::text,
    base_qry.simah_score::text,
    base_qry.customer_designation::text,
    base_qry.sector::text,
    base_qry.contact_no::text,
    base_qry.scheme1::text,
    base_qry.scheme::text,
    base_qry.profit_rate,
    base_qry.contract_status::text,
    base_qry.contract_status1::text,
    base_qry.rejected_stage::text,
    base_qry.rejected_date,
    base_qry.rejected_department::text,
    base_qry.rejected_department1::text,
    base_qry.pending_stage::text,
    base_qry.pending_with::text,
    base_qry.pending_since,
    base_qry.pending_department::text,
    base_qry.pending_department1::text,
    base_qry.app_entry_status::text,
    base_qry.rejection_reason::text,
    base_qry.promotion::text,
    base_qry.application_score::text,
    base_qry.score_range::text
FROM (
    SELECT
        base.application_no AS appid,
        cust.cifid AS customercif_id,
        base.application_date AS app_entry_date,
        base.snapshot_dt,
        base.product_type,
        base.contract_no,
        base.approved_date,
        base.funded_date,
        base.customer_segment,
        base.loan_amount,
        base.funded_amount,
        base.branch_code,
        base.branch_name,
        base.productcode,
        base.salesman_id,
        base.salesman,
        COALESCE(emp_magr.supervisorcode, 0) AS supervisorcode,
        base.customer_name_ar,
        base.customer_name_en,
        base.simah_score,
        base.customer_designation,
        base.sector,
        base.contact_no,
        base.scheme1,
        base.scheme,
        base.profit_rate,
        base.contract_status,
        base.contract_status1,
        base.rejected_stage,
        base.rejected_date,
        base.rejected_department,
        base.rejected_department1,
        base.pending_stage,
        base.pending_with,
        base.pending_since,
        base.pending_department,
        base.pending_department1,
        base.app_entry_status,
        base.rejection_reason,
        base.promotion,
        base.application_score,
        base.score_range
    FROM (
        SELECT
            application_date,
            application_no,
            contract_no,
            approved_date,
            funded_date,
            customer_segment,
            loan_amount,
            funded_amount,
            b.productcode,
            branch_code,
            branch_name,
            salesman_id,
            salesman,
            customer_name_ar,
            customer_name_en,
            product_type,
            simah_score,
            customer_designation,
            sector,
            contact_no,
            scheme1,
            scheme,
            profit_rate,
            contract_status,
            contract_status1,
            rejected_stage,
            rejected_date,
            rejected_department,
            rejected_department1,
            pending_stage,
            pending_with,
            pending_since,
            pending_department,
            pending_department1,
            app_entry_status,
            rejection_reason,
            promotion,
            application_score,
            score_range,
            COALESCE(
                application_date,
                approved_date,
                funded_date,
                rejected_date,
                pending_since
            ) AS snapshot_dt
        FROM reportingdw.stg_nfc_sales_with_status AS a
        JOIN reportingdw.stg_lot_globalloan_t AS b
            ON b.comp_appl_id = a.application_no
        WHERE COALESCE(
                application_date,
                approved_date,
                funded_date,
                rejected_date,
                pending_since
            )::date BETWEEN current_setting('etl.start_dt')::date
                AND current_setting('etl.end_dt')::date
    ) AS base
    LEFT JOIN (
        SELECT
            cifid,
            comp_appl_id,
            ROW_NUMBER() OVER (PARTITION BY comp_appl_id ORDER BY makedate DESC) AS ordr
        FROM reportingdw.stg_cif_customer_mx
        WHERE cifid IS NOT NULL
          AND comp_appl_id IS NOT NULL
    ) AS ccmx
        ON ccmx.comp_appl_id = base.application_no
       AND ccmx.ordr = 1
    LEFT JOIN reportingdw.stg_cif_customer AS cust
        ON ccmx.cifid = cust.cifid
    LEFT JOIN (
        SELECT
            employeecode,
            supervisorcode,
            productcode,
            makedate AS start_dt,
            COALESCE(
                LEAD(makedate) OVER (
                    PARTITION BY employeecode, productcode
                    ORDER BY makedate
                ),
                TIMESTAMP '9999-12-31'
            ) AS end_dt
        FROM reportingdw.stg_company_employee_role
        WHERE cg_rolecode = 'SLS'
          AND status <> 'X'
    ) AS emp_magr
        ON base.salesman_id = emp_magr.employeecode
       AND base.productcode = emp_magr.productcode
       AND base.application_date BETWEEN emp_magr.start_dt AND emp_magr.end_dt
) AS base_qry
LEFT JOIN reportingdw.dim_customer AS dimcust
    ON base_qry.customercif_id::text = dimcust.customercif_id
   AND dimcust.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_loan AS dimln
    ON base_qry.contract_no::text = dimln.loanno
   AND dimln.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_employee AS dimempsale
    ON base_qry.salesman_id::text = dimempsale.employeeid
   AND dimempsale.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_employee AS dimempmngr
    ON base_qry.supervisorcode::text = dimempmngr.employeeid
   AND dimempmngr.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_product AS dimprod
    ON base_qry.productcode::text = dimprod.productcode
   AND dimprod.end_dt = DATE '9999-12-31';
