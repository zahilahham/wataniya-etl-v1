import unittest

from app.sources import SqlServerTarget, _sqlserver_driver, sqlserver_odbc_connection_string


class SqlServerConnectionTests(unittest.TestCase):
    def test_connection_string_matches_the_nifi_encrypt_flags(self) -> None:
        target = SqlServerTarget(
            name="STG",
            host="db.example",
            port=1433,
            database="STG",
            user="etl.user",
            password="secret",
            encrypt=True,
            trust_server_certificate=True,
        )
        connection = sqlserver_odbc_connection_string(target, "ODBC Driver 18 for SQL Server")
        self.assertEqual(
            connection,
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=db.example,1433;"
            "DATABASE=STG;"
            "UID=etl.user;"
            "PWD=secret;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes",
        )

    def test_prefers_odbc_driver_18(self) -> None:
        installed = ["SQL Server", "ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server"]
        self.assertEqual(_sqlserver_driver(installed), "ODBC Driver 18 for SQL Server")

    def test_missing_driver_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            _sqlserver_driver(["SQL Server"])


if __name__ == "__main__":
    unittest.main()
