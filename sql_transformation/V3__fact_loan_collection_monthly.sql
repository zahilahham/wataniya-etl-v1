-- Latest collection status in each loan month, plus amounts collected in that distribution window.

CREATE TABLE IF NOT EXISTS reportingdw.fact_loan_collection_monthly (
    customer_sk bigint,
    loan_sk bigint,
    product_sk bigint,
    employee_sk bigint,
    loanno text,
    collection_month date,
    collected_amount numeric,
    due_amnt numeric,
    extra_paid_amount numeric,
    inst_amnt numeric,
    paid_flag text,
    dpd numeric,
    bucket text,
    prev_dpd numeric,
    bucket_movement text,
    rolling text,
    net_outstanding numeric,
    prev_net_outstanding numeric,
    collector_id text,
    collector_name text,
    remedial_flag text,
    writeoff_flag text,
    remedial_type text,
    status0 text,
    non_starter text
);

DELETE FROM reportingdw.fact_loan_collection_monthly AS tgt
USING (
    SELECT
        coll_desc.loanno,
        coll_desc.collection_month
    FROM (
        SELECT loanno, collection_month
        FROM (
            SELECT
                loanno,
                (
                    date_trunc('month', from_date::timestamp)
                    + INTERVAL '1 month'
                    - INTERVAL '1 day'
                )::date AS collection_month,
                ROW_NUMBER() OVER (
                    PARTITION BY loanid, EXTRACT(YEAR FROM from_date), EXTRACT(MONTH FROM from_date)
                    ORDER BY from_date DESC
                ) AS row_num
            FROM reportingdw.stg_lct_daily_coll_status
            WHERE from_date::date BETWEEN current_setting('etl.start_dt')::date
                AND current_setting('etl.end_dt')::date
        ) AS latest
        WHERE row_num = 1
    ) AS coll_desc
) AS src
WHERE tgt.loanno = src.loanno::text
  AND tgt.collection_month = src.collection_month;

INSERT INTO reportingdw.fact_loan_collection_monthly (
    customer_sk, loan_sk, product_sk, employee_sk, loanno, collection_month,
    collected_amount, due_amnt, extra_paid_amount, inst_amnt, paid_flag, dpd, bucket,
    prev_dpd, bucket_movement, rolling, net_outstanding, prev_net_outstanding,
    collector_id, collector_name, remedial_flag, writeoff_flag, remedial_type,
    status0, non_starter
)
SELECT
    dimcust.customer_sk,
    dimln.loan_sk,
    dimprod.product_sk,
    dimempcolctr.employee_sk,
    base_qry.loanno::text,
    base_qry.collection_month,
    base_qry.collected_amount,
    base_qry.due_amnt,
    base_qry.extra_paid_amount,
    base_qry.inst_amnt,
    base_qry.paid_flag,
    base_qry.dpd,
    base_qry.bucket,
    base_qry.prev_dpd,
    base_qry.bucket_movement,
    base_qry.rolling,
    base_qry.net_outstanding,
    base_qry.prev_net_outstanding,
    base_qry.collector_id::text,
    base_qry.collector_name::text,
    base_qry.remedial_flag::text,
    base_qry.writeoff_flag::text,
    base_qry.remedial_type::text,
    base_qry.status0::text,
    base_qry.non_starter
FROM (
    SELECT
        coll_desc.loanid,
        coll_desc.loanno,
        coll_desc.cifid,
        coll_desc.collection_month,
        COALESCE(coll.collected_amount, 0) AS collected_amount,
        coll_desc.due_amnt,
        CASE
            WHEN coll.collected_amount > coll_desc.due_amnt THEN coll.collected_amount - coll_desc.due_amnt
            ELSE 0
        END AS extra_paid_amount,
        coll_desc.inst_amnt,
        CASE
            WHEN coll.collected_amount > coll_desc.due_amnt THEN 'Y'
            WHEN coll.collected_amount IS NULL OR coll.collected_amount < coll_desc.due_amnt THEN 'N'
            WHEN coll.collected_amount = coll_desc.due_amnt AND coll_desc.due_amnt = coll_desc.inst_amnt THEN 'Y'
            ELSE 'Unknown'
        END AS paid_flag,
        coll_desc.dpd,
        coll_desc.bucket,
        coll_desc.prev_dpd,
        CASE
            WHEN coll_desc.prev_dpd = 0 OR coll_desc.dpd IS NULL THEN 'Bucket-0 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 0 AND coll_desc.prev_dpd <= 30 THEN 'Bucket-01 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 30 AND coll_desc.prev_dpd <= 60 THEN 'Bucket-02 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 60 AND coll_desc.prev_dpd <= 90 THEN 'Bucket-03 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 90 AND coll_desc.prev_dpd <= 120 THEN 'Bucket-04 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 120 AND coll_desc.prev_dpd <= 150 THEN 'Bucket-05 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 150 AND coll_desc.prev_dpd <= 180 THEN 'Bucket-06 TO ' || coll_desc.bucket
            WHEN coll_desc.prev_dpd > 180 THEN 'Remedial TO ' || coll_desc.bucket
        END AS bucket_movement,
        CASE
            WHEN coll_desc.dpd = 0 AND coll_desc.prev_dpd = 0 THEN 'RollBack'
            WHEN coll_desc.dpd = 0 THEN 'RollBack'
            WHEN coll_desc.prev_dpd = 0 AND coll_desc.dpd > 0 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 1 AND 30 AND coll_desc.dpd > 30 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 1 AND 30 AND coll_desc.dpd <= 30 THEN 'RollBack'
            WHEN coll_desc.prev_dpd BETWEEN 31 AND 60 AND coll_desc.dpd > 60 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 31 AND 60 AND coll_desc.dpd <= 60 THEN 'RollBack'
            WHEN coll_desc.prev_dpd BETWEEN 61 AND 90 AND coll_desc.dpd > 90 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 61 AND 90 AND coll_desc.dpd <= 90 THEN 'RollBack'
            WHEN coll_desc.prev_dpd BETWEEN 91 AND 120 AND coll_desc.dpd > 120 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 91 AND 120 AND coll_desc.dpd <= 120 THEN 'RollBack'
            WHEN coll_desc.prev_dpd BETWEEN 121 AND 150 AND coll_desc.dpd > 150 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 121 AND 150 AND coll_desc.dpd <= 150 THEN 'RollBack'
            WHEN coll_desc.prev_dpd BETWEEN 151 AND 180 AND coll_desc.dpd > 180 THEN 'Rollward'
            WHEN coll_desc.prev_dpd BETWEEN 151 AND 180 AND coll_desc.dpd <= 180 THEN 'RollBack'
            ELSE 'Rollward'
        END AS rolling,
        coll_desc.net_outstanding,
        coll_desc.prev_net_outstanding,
        coll_desc.collector_id,
        coll_desc.collector_name,
        coll_desc.remedial_flag,
        coll_desc.writeoff_flag,
        coll_desc.remedial_type,
        coll_desc.status0,
        coll_desc.non_starter
    FROM (
        SELECT
            loanid,
            loanno,
            cifid,
            from_date,
            collection_month,
            due_amnt,
            inst_amnt,
            dpd,
            bucket,
            COALESCE(LAG(dpd) OVER (PARTITION BY loanid ORDER BY from_date), 0) AS prev_dpd,
            net_outstanding,
            LAG(net_outstanding) OVER (PARTITION BY loanid ORDER BY from_date) AS prev_net_outstanding,
            collector_name,
            collector_id,
            remedial_flag,
            writeoff_flag,
            remedial_type,
            status0,
            non_starter
        FROM (
            SELECT
                loanid,
                loanno,
                cifid,
                COALESCE(current_late_amt, 0) AS due_amnt,
                monthlyinstamount AS inst_amnt,
                COALESCE(total_outstanding, 0) AS net_outstanding,
                from_date,
                (
                    date_trunc('month', from_date::timestamp)
                    + INTERVAL '1 month'
                    - INTERVAL '1 day'
                )::date AS collection_month,
                COALESCE(dpd, 0) AS dpd,
                CASE
                    WHEN dpd = 0 OR dpd IS NULL THEN 'Bucket-0'
                    WHEN dpd > 0 AND dpd <= 30 THEN 'Bucket-01'
                    WHEN dpd > 30 AND dpd <= 60 THEN 'Bucket-02'
                    WHEN dpd > 60 AND dpd <= 90 THEN 'Bucket-03'
                    WHEN dpd > 90 AND dpd <= 120 THEN 'Bucket-04'
                    WHEN dpd > 120 AND dpd <= 150 THEN 'Bucket-05'
                    WHEN dpd > 150 AND dpd <= 180 THEN 'Bucket-06'
                    WHEN dpd > 180 THEN 'Remedial'
                END AS bucket,
                COALESCE(collector_name, '0') AS collector_name,
                COALESCE(collector_id, '0') AS collector_id,
                COALESCE(remedial_flag, 'N') AS remedial_flag,
                writeoff_flag,
                substatus_flag AS remedial_type,
                status AS status0,
                'YES' AS non_starter,
                ROW_NUMBER() OVER (
                    PARTITION BY loanid, EXTRACT(YEAR FROM from_date), EXTRACT(MONTH FROM from_date)
                    ORDER BY from_date DESC
                ) AS row_num
            FROM reportingdw.stg_lct_daily_coll_status
            WHERE from_date::date BETWEEN current_setting('etl.start_dt')::date
                AND current_setting('etl.end_dt')::date
        ) AS latest
        WHERE row_num = 1
    ) AS coll_desc
    LEFT JOIN (
        SELECT
            lmad.loanid,
            mnth_dist.coll_month AS collection_month,
            SUM(lmad.collected_amount) AS collected_amount
        FROM (
            SELECT
                (
                    date_trunc('month', from_date::timestamp)
                    + INTERVAL '1 month'
                    - INTERVAL '1 day'
                )::date AS coll_month,
                from_date::date AS month_start_dt,
                dist_date_next_month::date AS month_end_dt
            FROM reportingdw.stg_coll_month_distribution
            WHERE (
                date_trunc('month', from_date::timestamp)
                + INTERVAL '1 month'
                - INTERVAL '1 day'
            )::date BETWEEN current_setting('etl.start_dt')::date
                AND current_setting('etl.end_dt')::date
        ) AS mnth_dist
        JOIN (
            SELECT
                loanid,
                makedate::date AS coll_date,
                SUM(amt_adj) AS collected_amount
            FROM reportingdw.stg_lmt_appropriated_data
            GROUP BY loanid, makedate::date
        ) AS lmad
            ON lmad.coll_date >= mnth_dist.month_start_dt
           AND lmad.coll_date <= mnth_dist.month_end_dt
        GROUP BY lmad.loanid, mnth_dist.coll_month
    ) AS coll
        ON coll_desc.loanid = coll.loanid
       AND coll_desc.collection_month = coll.collection_month
) AS base_qry
LEFT JOIN reportingdw.dim_customer AS dimcust
    ON base_qry.cifid::text = dimcust.customercif_id
   AND dimcust.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_loan AS dimln
    ON base_qry.loanno::text = dimln.loanno
   AND dimln.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_employee AS dimempcolctr
    ON base_qry.collector_id::text = dimempcolctr.employeeid
   AND dimempcolctr.end_dt = DATE '9999-12-31'
LEFT JOIN reportingdw.dim_product AS dimprod
    ON dimln.productcode = dimprod.productcode
   AND dimprod.end_dt = DATE '9999-12-31';
