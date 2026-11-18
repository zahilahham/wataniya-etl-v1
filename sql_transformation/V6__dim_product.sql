-- Product version joined to the current scheme. Runs after dim_scheme.

CREATE TABLE IF NOT EXISTS reportingdw.dim_product (
    product_sk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    productcode text,
    description text,
    status text,
    effective_date timestamp,
    prod_dmcode text,
    product_limit numeric,
    scheme_sk bigint,
    start_dt date,
    end_dt date
);

CREATE UNIQUE INDEX IF NOT EXISTS dim_product_productcode_start_dt_idx
    ON reportingdw.dim_product (productcode, start_dt);

INSERT INTO reportingdw.dim_product (
    productcode,
    description,
    status,
    effective_date,
    prod_dmcode,
    product_limit,
    scheme_sk,
    start_dt,
    end_dt
)
SELECT
    base.productcode::text,
    base.description::text,
    base.status::text,
    base.effective_date,
    base.prod_dmcode::text,
    base.product_limit,
    dimschm.scheme_sk,
    base.start_dt,
    DATE '9999-12-31'
FROM (
    SELECT
        prd.productcode,
        prd.description,
        prd.status,
        prd.effective_date,
        prd.prod_dmcode,
        prd.product_limit,
        prdschm.schemeid,
        prd.start_dt
    FROM (
        SELECT
            productcode,
            description,
            makedate::date AS start_dt,
            effective_date,
            prod_dmcode,
            status,
            product_limit,
            ROW_NUMBER() OVER (PARTITION BY productcode ORDER BY makedate DESC) AS rn
        FROM reportingdw.stg_product
        WHERE makedate::date BETWEEN current_setting('etl.start_dt')::date
            AND current_setting('etl.end_dt')::date
    ) AS prd
    LEFT JOIN (
        SELECT schemeid, productcode
        FROM (
            SELECT
                schemeid,
                productcode,
                ROW_NUMBER() OVER (PARTITION BY productcode ORDER BY makedate DESC) AS rn
            FROM reportingdw.stg_prd_scheme
        ) AS schemes
        WHERE rn = 1
    ) AS prdschm
        ON prd.productcode = prdschm.productcode
    WHERE prd.rn = 1
) AS base
LEFT JOIN reportingdw.dim_scheme AS dimschm
    ON base.schemeid::text = dimschm.schemeid
   AND dimschm.end_dt = DATE '9999-12-31'
WHERE NOT EXISTS (
    SELECT 1
    FROM reportingdw.dim_product AS existing
    WHERE existing.productcode = base.productcode::text
      AND existing.start_dt = base.start_dt
);

WITH open_rows AS (
    SELECT
        product_sk,
        (
            LEAD(start_dt) OVER (PARTITION BY productcode ORDER BY start_dt)
            - INTERVAL '1 day'
        )::date AS new_end
    FROM reportingdw.dim_product
    WHERE end_dt = DATE '9999-12-31'
)
UPDATE reportingdw.dim_product AS dim
SET end_dt = open_rows.new_end
FROM open_rows
WHERE dim.product_sk = open_rows.product_sk
  AND open_rows.new_end IS NOT NULL;
