import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import myos_compact
except ModuleNotFoundError:  # 该模块需要带 mcp 的 Python 3.14
    myos_compact = None


@unittest.skipIf(myos_compact is None, "mcp client Python (3.14) required")
class SummaryTest(unittest.TestCase):
    def test_summary_carries_mount_root(self):
        compact = {
            "caseMaterialId": "m1",
            "materialName": "phone.zip",
            "mountPath": r"\\?\C:\osmap\GUID_20260101\Root",
            "overview": {"analysisMode": "sqlite_first"},
            "mfsStats": {"appCount": 0, "totalAppDataCount": 0, "apps": []},
            "summary": {},
            "sqliteQueryHints": [],
        }
        text = myos_compact.build_summary(compact)
        self.assertIn("mountPath=", text)
        self.assertIn(r"C:\osmap\GUID_20260101\Root", text)


if __name__ == "__main__":
    unittest.main()
