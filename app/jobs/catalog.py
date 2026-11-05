from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Job:
    name: str
    kind: str
    enabled: bool
    description: str


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
    "cccallview",
    "dagentperformanceview",
    "iagentperformancestat",
    "agentloginlogoutview",
)

_PLANNED_TRANSFORMS = (
    "020_lot_loan_t",
    "030_product",
    "040_lct_loan_dtl",
    "050_lct_daily_coll_status",
    "060_prd_scheme",
    "070_coll_month_distribution",
    "080_company_generic",
    "090_ext_simah_rpt_header",
    "100_lmt_rcpt_dtl",
    "110_lot_globalloan_t",
    "120_lmt_loan_dtl",
    "130_lmt_appropriated_data",
    "140_cif_customer_mx",
    "150_lot_penaltyinterestrate_dtl",
    "160_cif_employment_dtl",
    "170_cif_identification_details",
    "180_company_employee_role",
    "190_cif_custincomebreakup_hdr",
    "200_nfc_sales_with_status",
    "210_cif_address",
    "220_mis_sale_target",
    "230_collection_target",
    "240_cif_customer",
    "250_lot_employment_dtl",
    "260_dim_customer",
    "270_dim_loan",
    "280_dim_scheme",
    "290_dim_product",
    "300_dim_company_generic",
    "310_fact_app_cust_product",
    "320_fact_emp_target",
    "330_fact_loan_collection_monthly",
    "340_fact_avaya",
    "350_fact_agent_session",
    "360_fact_agent_performance",
    "370_fact_agent_performance_stat",
    "380_cccallview",
    "390_dagentperformanceview",
    "400_iagentperformancestat",
    "410_agentloginlogoutview",
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
    Job(
        name="010_employee",
        kind="transform",
        enabled=True,
        description="Builds reportingdw.stg_employee and reportingdw.dim_employee",
    ),
    *(
        Job(
            name=name,
            kind="transform",
            enabled=False,
            description="Placeholder folder. Add V1__transformation_job.sql to include it.",
        )
        for name in _PLANNED_TRANSFORMS
    ),
)

PLANNED_TRANSFORM_FOLDERS = _PLANNED_TRANSFORMS


def list_jobs() -> list[dict[str, object]]:
    return [asdict(job) for job in JOBS]


def get_extract_job(name: str) -> Job | None:
    for job in JOBS:
        if job.kind == "extract" and job.name == name:
            return job
    return None
