import tempfile
import unittest
from pathlib import Path

from app.etl.transform import _is_executable, list_transformation_files, split_sql


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

    def test_employee_transformation_has_seven_statements(self) -> None:
        script_path = Path(__file__).resolve().parents[1] / "sql_transformation" / "010_employee" / "V1__transformation_job.sql"
        script = script_path.read_text(encoding="utf-8")
        statements = [item for item in split_sql(script) if _is_executable(item)]
        self.assertEqual(len(statements), 7)
        self.assertIn("reportingdw.stg_employee", statements[0])
        self.assertIn("reportingdw.dim_employee", statements[3])
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
    def test_files_are_sorted_by_folder_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("030_product", "010_employee", "020_scheme"):
                folder = root / name
                folder.mkdir()
                (folder / "V1__transformation_job.sql").write_text("SELECT 1;", encoding="utf-8")
            (root / "040_empty").mkdir()
            found = [path.parent.name for path in list_transformation_files(root)]
        self.assertEqual(found, ["010_employee", "020_scheme", "030_product"])


if __name__ == "__main__":
    unittest.main()
