import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ios_backup_probe


class SumByUuidTest(unittest.TestCase):
    def test_same_amount_different_ids_both_count(self):
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "ledger.sqlite"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE t (id TEXT, money INTEGER)")
            con.executemany("INSERT INTO t VALUES (?, ?)", [("a", 10000), ("b", 10000), ("a", 10000)])
            con.commit()
            con.close()
            buf = StringIO()
            with redirect_stdout(buf):
                ios_backup_probe.sum_by_uuid(str(db), "t", "id", "money")
        out = buf.getvalue()
        self.assertIn("SUM 20000", out)
        self.assertNotIn("SUM 10000", out)


if __name__ == "__main__":
    unittest.main()
