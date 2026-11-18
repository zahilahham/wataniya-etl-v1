import tempfile
import unittest
from pathlib import Path

from app.etl.transform import _is_executable, list_transformation_files, split_sql

ROOT = Path(__file__).resolve().parents[1]


def _read_sql(name: str) -> str:
    return (ROOT / "sql_transformation" / name).read_text(encoding="utf-8")


class SplitSqlTests(unittest.TestCase):
    def test_splits_on_semicolons(self) -> None:
        self.assertEqual(split_sql("SELECT 1; SELECT 2;"), ["SELECT 1", "SELECT 2"])

    def test_keeps_a_statement_without_a_trailing_semicolon(self) -> None:
        self.assertEqual(split_sql("SELECT 1"), ["SELECT 1"])

    def test_keeps_semicolons_inside_quotes(self) -> None:
        script = "SELECT 'a;b'; SELECT 2;"
        self.assertEqual(split_sql(script), ["SELECT 'a;b'", "SELECT 2"])

    def test_keeps_escaped_quotes(self) -> None:
        script = "SELECT 'it'';s; fine'; SELECT 2;"
        self.assertEqual(split_sql(script), ["SELECT 'it'';s; fine'", "SELECT 2"])

    def test_keeps_semicolons_inside_dollar_quotes(self) -> None:
        script = "SELECT $$ a; b $$; SELECT $body$ x; y $body$;"
        self.assertEqual(
            split_sql(script),
            ["SELECT $$ a; b $$", "SELECT $body$ x; y $body$"],
        )

    def test_ignores_semicolons_in_comments(self) -> None:
        script = "SELECT 1;\n-- note; still a comment\nSELECT 2; /* hide; */"
        self.assertEqual(split_sql(script), ["SELECT 1", "-- note; still a comment\nSELECT 2", "/* hide; */"])

    def test_does_not_split_a_quoted_identifier(self) -> None:
        self.assertEqual(split_sql('SELECT "a;b"; SELECT 2;'), ['SELECT "a;b"', "SELECT 2"])

    def test_empty_script(self) -> None:
        self.assertEqual(split_sql("  \n-- only comment\n"), ["-- only comment"])

    def test_comment_only_text_is_not_executable(self) -> None:
        self.assertFalse(_is_executable("-- note; still a comment"))
        self.assertFalse(_is_executable("/* hide; */"))
        self.assertTrue(_is_executable("SELECT 1"))

    def test_employee_staging_has_three_statements(self) -> None:
        script = _read_sql("V1__stg_raw_employee.sql")
        statements = [item for item in split_sql(script) if _is_executable(item)]
        self.assertEqual(len(statements), 3)
        self.assertIn("reportingdw.stg_employee", statements[0])
        self.assertNotIn("reportingdw.dim_employee", script)

    def test_employee_dimension_has_four_statements(self) -> None:
        script = _read_sql("V2__dim_employee.sql")
        statements = [item for item in split_sql(script) if _is_executable(item)]
        self.assertEqual(len(statements), 4)
        self.assertIn("reportingdw.dim_employee", statements[0])
        self.assertTrue(statements[-1].lstrip().upper().startswith("WITH"))


class OracleTypeTests(unittest.TestCase):
    def test_number_date_and_text_mapping(self) -> None:
        from app.etl.extract_load import map_oracle_type

        self.assertEqual(map_oracle_type(type("T", (), {"name": "DB_TYPE_NUMBER"})()), "numeric")
        self.assertEqual(map_oracle_type(type("T", (), {"name": "DB_TYPE_DATE"})()), "timestamp")
        self.assertEqual(map_oracle_type(type("T", (), {"name": "DB_TYPE_VARCHAR"})()), "text")
        self.assertEqual(map_oracle_type(type("T", (), {"name": "DB_TYPE_CLOB"})()), "text")
        self.assertEqual(map_oracle_type(object()), "text")


class TransformationOrderTests(unittest.TestCase):
    def test_files_run_in_version_order_for_the_requested_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "V10__stg_late.sql",
                "V2__stg_second.sql",
                "V1__stg_employee.sql",
                "V1__dim_employee.sql",
                "V1__fact_avaya.sql",
            ):
                (root / name).write_text("SELECT 1;", encoding="utf-8")
            staging = [path.name for path in list_transformation_files(root, "staging")]
            dimension = [path.name for path in list_transformation_files(root, "dimension")]
            fact = [path.name for path in list_transformation_files(root, "fact")]
        self.assertEqual(staging, ["V1__stg_employee.sql", "V2__stg_second.sql", "V10__stg_late.sql"])
        self.assertEqual(dimension, ["V1__dim_employee.sql"])
        self.assertEqual(fact, ["V1__fact_avaya.sql"])

    def test_duplicate_version_in_one_layer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "V1__stg_employee.sql").write_text("SELECT 1;", encoding="utf-8")
            (root / "V1__stg_product.sql").write_text("SELECT 1;", encoding="utf-8")
            with self.assertRaises(ValueError):
                list_transformation_files(root, "staging")

    def test_a_file_without_a_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "stg_employee.sql").write_text("SELECT 1;", encoding="utf-8")
            with self.assertRaises(ValueError):
                list_transformation_files(root, "staging")


class LayerCatalogTests(unittest.TestCase):
    def test_names_use_the_source_schema_only_outside_the_warehouse(self) -> None:
        from app.jobs.catalog import JOBS, LAYERS

        self.assertEqual(LAYERS, ("staging", "dimension", "fact"))
        staging = [job.name for job in JOBS if job.layer == "staging"]
        dimension = [job.name for job in JOBS if job.layer == "dimension"]
        fact = [job.name for job in JOBS if job.layer == "fact"]
        self.assertEqual(
            [int(name.split("__", 1)[0][1:]) for name in staging],
            list(range(1, len(staging) + 1)),
        )
        self.assertTrue(all(name.split("__", 1)[1].startswith("stg_raw_") for name in staging))
        self.assertEqual(
            [int(name.split("__", 1)[0][1:]) for name in dimension],
            list(range(2, len(dimension) + 2)),
        )
        self.assertTrue(all(name.split("__", 1)[1].startswith("dim_") for name in dimension))
        self.assertEqual(
            [int(name.split("__", 1)[0][1:]) for name in fact],
            list(range(1, len(fact) + 1)),
        )
        self.assertTrue(all("__stg_" not in name and "__raw_" not in name for name in fact))

    def test_every_enabled_transform_has_a_sql_file(self) -> None:
        from app.jobs.catalog import EXTRACT_SPECS, JOBS
        from app.etl.extract_load import build_extract_query
        from datetime import date

        sql_dir = ROOT / "sql_transformation"
        for job in JOBS:
            self.assertTrue(job.enabled)
            if job.kind != "transform":
                self.assertIn(job.name, EXTRACT_SPECS)
                continue
            self.assertTrue((sql_dir / f"{job.name}.sql").is_file(), job.name)

        start = date(2026, 6, 1)
        end = date(2026, 6, 2)
        generic_sql, generic_binds = build_extract_query(
            "PULSE_NFC_PROD", EXTRACT_SPECS["company_generic"], start, end
        )
        self.assertIn("KEY AS KEY_MS", generic_sql)
        self.assertIn("ROWNUM <= 100000", generic_sql)
        self.assertEqual(generic_binds, {})
        sales_sql, sales_binds = build_extract_query(
            "PULSE_NFC_PROD", EXTRACT_SPECS["nfc_sales_with_status"], start, end
        )
        self.assertIn("COALESCE(APPLICATION_DATE", sales_sql)
        self.assertEqual(set(sales_binds), {"start_dt", "end_dt_exclusive"})
        full_sql, full_binds = build_extract_query(
            "PULSE_NFC_PROD", EXTRACT_SPECS["mis_sale_target"], start, end
        )
        self.assertNotIn("WHERE", full_sql)
        self.assertEqual(full_binds, {})
        from app.jobs.catalog import load_sequence

        steps = load_sequence()
        self.assertEqual(steps[0], ("extract", "employee"))
        self.assertEqual(steps[-3:], (("transform", "staging"), ("transform", "dimension"), ("transform", "fact")))
        self.assertEqual(len([kind for kind, _ in steps if kind == "extract"]), 25)
        self.assertEqual(
            [path.name for path in list_transformation_files(sql_dir, "fact")],
            [
                "V1__fact_app_cust_product.sql",
                "V2__fact_emp_target.sql",
                "V3__fact_loan_collection_monthly.sql",
            ],
        )


if __name__ == "__main__":
    unittest.main()
