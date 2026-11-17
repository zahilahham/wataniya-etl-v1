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

_PLACEHOLDER = "Placeholder. Add the matching V{n}__name.sql file to include it."

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
            enabled=(layer, name) in _LIVE,
            description=_LIVE.get((layer, name), _PLACEHOLDER),
            layer=layer,
        )
        for name in names
    )


JOBS: tuple[Job, ...] = (
    Job(
        name="employee",
        kind="extract",
        enabled=True,
        description="Oracle EMPLOYEE filtered on MAKEDATE, loaded as-is into raw.employee",
    ),
    *(
        Job(
            name=name,
            kind="extract",
            enabled=False,
            description="Planned extract. The Python load is not wired yet.",
        )
        for name in _KASTLE_EXTRACTS
    ),
    *_layer_jobs("staging", _versioned("staging", _STAGING_OBJECTS)),
    *_layer_jobs("dimension", _versioned("dimension", _DIMENSION_OBJECTS, start=2)),
    *_layer_jobs("fact", _versioned("fact", _FACT_OBJECTS)),
)


def list_jobs() -> list[dict[str, object]]:
    return [asdict(job) for job in JOBS]


def get_extract_job(name: str) -> Job | None:
    for job in JOBS:
        if job.kind == "extract" and job.name == name:
            return job
    return None
