import plistlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ios_backup_probe


class DeviceProbeTest(unittest.TestCase):
    def _run(self, build):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            build(root)
            buf = StringIO()
            with redirect_stdout(buf):
                ios_backup_probe.device(str(root))
        return buf.getvalue()

    def test_reads_serial_from_manifest_plist(self):
        def build(root):
            info = root / "Platform" / "DeviceInfo"
            info.mkdir(parents=True)
            (info / "Manifest.plist").write_bytes(plistlib.dumps({
                "Lockdown": {"ProductSerialNumber": "TESTSERIAL01", "ProductType": "iPhone12,1"},
                "DeviceName": "leeIPhone",
            }))

        out = self._run(build)
        self.assertIn("SERIAL TESTSERIAL01", out)
        self.assertIn("leeIPhone", out)

    def test_serial_from_manifest_xml_without_plist(self):
        def build(root):
            info = root / "Platform" / "DeviceInfo"
            info.mkdir(parents=True)
            (info / "Manifest.xml").write_text(
                '<?xml version="1.0"?><plist><dict>'
                '<key>SerialNumber</key><string>XMLSERIAL01</string>'
                '</dict></plist>', encoding="utf-8")

        out = self._run(build)
        self.assertIn("SERIAL XMLSERIAL01", out)

    def test_missing_serial_fails_loudly(self):
        def build(root):
            (root / "Platform" / "DeviceInfo").mkdir(parents=True)
        with self.assertRaises(SystemExit):
            self._run(build)


if __name__ == "__main__":
    unittest.main()
