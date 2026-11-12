import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import myos_computer_compact
except ModuleNotFoundError:
    myos_computer_compact = None


@unittest.skipIf(myos_computer_compact is None, "mcp client Python (3.14) required")
class SummaryTest(unittest.TestCase):
    def test_summary_carries_mount_path_per_material(self):
        compact = {
            "caseId": "c1",
            "caseName": "demo",
            "generated": "t",
            "materials": [{
                "materialDirName": "disk.001",
                "pluginCount": 0,
                "materialDir": "D:/dev/disk.001",
                "mountPath": r"C:\osmap\GUID\Root",
                "online": False,
                "plugins": [],
                "errors": [],
            }],
        }
        text = myos_computer_compact.build_summary(compact)
        self.assertIn("mountPath=", text)
        self.assertIn(r"C:\osmap\GUID\Root", text)
        self.assertIn("online=False", text)


if __name__ == "__main__":
    unittest.main()
