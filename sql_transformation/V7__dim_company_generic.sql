-- Overwrite dim_company_generic on genericid. KEY landed in raw as key_ms.

CREATE TABLE IF NOT EXISTS reportingdw.dim_company_generic (
    genericid text PRIMARY KEY,
    companyid text,
    key_ms text,
    value text,
    makerid text,
    makedate timestamp,
    status text,
    authorid text,
    authdate timestamp,
    description text,
    parentkey text,
    remarks text,
    legacycode1 text,
    legacycode2 text,
    legacycode3 text,
    legacycode4 text,
    description2 text,
    description3 text,
    legacycode5 text,
    moduleid text,
    dmcode text
);

UPDATE reportingdw.dim_company_generic AS tgt
SET
    companyid = src.companyid::text,
    key_ms = src.key_ms::text,
    value = src.value::text,
    makerid = src.makerid::text,
    makedate = src.makedate,
    status = src.status::text,
    authorid = src.authorid::text,
    authdate = src.authdate,
    description = src.description::text,
    parentkey = src.parentkey::text,
    remarks = src.remarks::text,
    legacycode1 = src.legacycode1::text,
    legacycode2 = src.legacycode2::text,
    legacycode3 = src.legacycode3::text,
    legacycode4 = src.legacycode4::text,
    description2 = src.description2::text,
    description3 = src.description3::text,
    legacycode5 = src.legacycode5::text,
    moduleid = src.moduleid::text,
    dmcode = src.dmcode::text
FROM reportingdw.stg_company_generic AS src
WHERE tgt.genericid = src.genericid::text;

INSERT INTO reportingdw.dim_company_generic (
    genericid, companyid, key_ms, value, makerid, makedate, status, authorid, authdate,
    description, parentkey, remarks, legacycode1, legacycode2, legacycode3, legacycode4,
    description2, description3, legacycode5, moduleid, dmcode
)
SELECT
    src.genericid::text,
    src.companyid::text,
    src.key_ms::text,
    src.value::text,
    src.makerid::text,
    src.makedate,
    src.status::text,
    src.authorid::text,
    src.authdate,
    src.description::text,
    src.parentkey::text,
    src.remarks::text,
    src.legacycode1::text,
    src.legacycode2::text,
    src.legacycode3::text,
    src.legacycode4::text,
    src.description2::text,
    src.description3::text,
    src.legacycode5::text,
    src.moduleid::text,
    src.dmcode::text
FROM reportingdw.stg_company_generic AS src
WHERE NOT EXISTS (
    SELECT 1
    FROM reportingdw.dim_company_generic AS tgt
    WHERE tgt.genericid = src.genericid::text
);
