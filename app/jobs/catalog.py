from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Job:
    name: str
    kind: str
    enabled: bool
    description: str
    layer: str | None = None


LAYERS = ("staging", "dimension", "fact")

LAYER_PREFIX = {
    "staging": "stg_",
    "dimension": "dim_",
    "fact": "fact_",
}

_KASTLE_EXTRACTS = (
    "lot_loan_t",
    "product",
    "lct_loan_dtl",
    "lct_daily_coll_status",
    "prd_scheme",
    "coll_month_distribution",
    "company_generic",
    "ext_simah_rpt_header",
    "lmt_rcpt_dtl",
    "lot_globalloan_t",
    "lmt_loan_dtl",
    "lmt_appropriated_data",
    "cif_customer_mx",
    "lot_penaltyinterestrate_dtl",
    "cif_employment_dtl",
    "cif_identification_details",
    "company_employee_role",
    "cif_custincomebreakup_hdr",
    "nfc_sales_with_status",
    "cif_address",
    "mis_sale_target",
    "collection_target",
    "cif_customer",
    "lot_employment_dtl",
)

_STAGING_OBJECTS = (
    "employee",
    "lot_loan_t",
    "product",
    "lct_loan_dtl",
    "lct_daily_coll_status",
    "prd_scheme",
    "coll_month_distribution",
    "company_generic",
    "ext_simah_rpt_header",
    "lmt_rcpt_dtl",
    "lot_globalloan_t",
    "lmt_loan_dtl",
    "lmt_appropriated_data",
    "cif_customer_mx",
    "lot_penaltyinterestrate_dtl",
    "cif_employment_dtl",
    "cif_identification_details",
    "company_employee_role",
    "cif_custincomebreakup_hdr",
    "nfc_sales_with_status",
    "cif_address",
    "mis_sale_target",
    "collection_target",
    "cif_customer",
    "lot_employment_dtl",
)

_DIMENSION_OBJECTS = (
    "employee",
    "customer",
    "loan",
    "scheme",
    "product",
    "company_generic",
)

_FACT_OBJECTS = (
    "app_cust_product",
    "emp_target",
    "loan_collection_monthly",
)

@dataclass(frozen=True)
class ExtractSpec:
    source: str
    where: str | None = None
    columns: str = "*"


_MAKEDATE = "MAKEDATE >= :start_dt AND MAKEDATE < :end_dt_exclusive"
_SALES_DATE = (
    "COALESCE(APPLICATION_DATE, APPROVED_DATE, FUNDED_DATE, REJECTED_DATE, PENDING_SINCE) >= :start_dt "
    "AND COALESCE(APPLICATION_DATE, APPROVED_DATE, FUNDED_DATE, REJECTED_DATE, PENDING_SINCE) < :end_dt_exclusive"
)
_COMPANY_GENERIC_COLUMNS = (
    "GENERICID, COMPANYID, KEY AS KEY_MS, VALUE, MAKERID, MAKEDATE, STATUS, AUTHORID, AUTHDATE, "
    "DESCRIPTION, PARENTKEY, REMARKS, LEGACYCODE1, LEGACYCODE2, LEGACYCODE3, LEGACYCODE4, "
    "DESCRIPTION2, DESCRIPTION3, LEGACYCODE5, MODULEID, DMCODE"
)

EXTRACT_SPECS: dict[str, ExtractSpec] = {
    "employee": ExtractSpec("EMPLOYEE", _MAKEDATE),
    "lot_loan_t": ExtractSpec("LOT_LOAN_T", _MAKEDATE),
    "product": ExtractSpec("PRODUCT", _MAKEDATE),
    "lct_loan_dtl": ExtractSpec("LCT_LOAN_DTL", _MAKEDATE),
    "lct_daily_coll_status": ExtractSpec(
        "LCT_DAILY_COLL_STATUS",
        "FROM_DATE >= :start_dt AND FROM_DATE < :end_dt_exclusive",
    ),
    "prd_scheme": ExtractSpec("PRD_SCHEME", _MAKEDATE),
    "coll_month_distribution": ExtractSpec("COLL_MONTH_DISTRIBUTION"),
    "company_generic": ExtractSpec(
        "COMPANY_GENERIC",
        "ROWNUM <= 100000",
        _COMPANY_GENERIC_COLUMNS,
    ),
    "ext_simah_rpt_header": ExtractSpec("EXT_SIMAH_RPT_HEADER", _MAKEDATE),
    "lmt_rcpt_dtl": ExtractSpec("LMT_RCPT_DTL", _MAKEDATE),
    "lot_globalloan_t": ExtractSpec("LOT_GLOBALLOAN_T", _MAKEDATE),
    "lmt_loan_dtl": ExtractSpec("LMT_LOAN_DTL", _MAKEDATE),
    "lmt_appropriated_data": ExtractSpec("LMT_APPROPRIATED_DATA", _MAKEDATE),
    "cif_customer_mx": ExtractSpec("CIF_CUSTOMER_MX", _MAKEDATE),
    "lot_penaltyinterestrate_dtl": ExtractSpec("LOT_PENALTYINTERESTRATE_DTL", _MAKEDATE),
    "cif_employment_dtl": ExtractSpec("CIF_EMPLOYMENT_DTL", _MAKEDATE),
    "cif_identification_details": ExtractSpec("CIF_IDENTIFICATION_DETAILS", _MAKEDATE),
    "company_employee_role": ExtractSpec("COMPANY_EMPLOYEE_ROLE", _MAKEDATE),
    "cif_custincomebreakup_hdr": ExtractSpec("CIF_CUSTINCOMEBREAKUP_HDR", _MAKEDATE),
    "nfc_sales_with_status": ExtractSpec("NFC_SALES_WITH_STATUS", _SALES_DATE),
    "cif_address": ExtractSpec("CIF_ADDRESS", _MAKEDATE),
    "mis_sale_target": ExtractSpec("MIS_SALE_TARGET"),
    "collection_target": ExtractSpec("COLLECTION_TARGET"),
    "cif_customer": ExtractSpec("CIF_CUSTOMER", _MAKEDATE),
    "lot_employment_dtl": ExtractSpec("LOT_EMPLOYMENT_DTL", _MAKEDATE),
}

_LIVE = {
    ("staging", "V1__stg_raw_employee"): "Copies raw.employee into reportingdw.stg_employee",
    ("dimension", "V2__dim_employee"): "Builds reportingdw.dim_employee from reportingdw.stg_employee",
}


def _versioned(layer: str, objects: tuple[str, ...], start: int = 1) -> tuple[str, ...]:
    prefix = "stg_raw_" if layer == "staging" else LAYER_PREFIX[layer]
    return tuple(f"V{number}__{prefix}{name}" for number, name in enumerate(objects, start=start))


def _layer_jobs(layer: str, names: tuple[str, ...]) -> tuple[Job, ...]:
    return tuple(
        Job(
            name=name,
            kind="transform",
            enabled=True,
            description=_LIVE.get((layer, name), f"Runs {name}"),
            layer=layer,
        )
        for name in names
    )


JOBS: tuple[Job, ...] = (
    *(
        Job(
            name=name,
            kind="extract",
            enabled=True,
            description=f"Oracle {EXTRACT_SPECS[name].source} loaded into raw.{name}",
        )
        for name in ("employee", *_KASTLE_EXTRACTS)
    ),
    *_layer_jobs("staging", _versioned("staging", _STAGING_OBJECTS)),
    *_layer_jobs("dimension", _versioned("dimension", _DIMENSION_OBJECTS, start=2)),
    *_layer_jobs("fact", _versioned("fact", _FACT_OBJECTS)),
)


def list_jobs() -> list[dict[str, object]]:
    return [asdict(job) for job in JOBS]


def load_sequence() -> tuple[tuple[str, str], ...]:
    """Extracts in catalog order, then staging, dimension, and fact."""
    steps = [("extract", job.name) for job in JOBS if job.kind == "extract" and job.enabled]
    steps.extend(("transform", layer) for layer in LAYERS)
    return tuple(steps)


def get_extract_job(name: str) -> Job | None:
    for job in JOBS:
        if job.kind == "extract" and job.name == name:
            return job
    return None
