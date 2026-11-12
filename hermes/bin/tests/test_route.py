import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dfir_router


class RouteTest(unittest.TestCase):
    def test_plain_mobile_is_not_ios(self):
        self.assertEqual(dfir_router.route("请做手机取证"),
                         {"skill": None, "command": None, "forbid": None, "index_file": None})
        self.assertEqual(dfir_router.local_skill("请做手机取证"), "mobile-ctf-pipeline")

    def test_remote_without_sunflower(self):
        jump = dfir_router.route("曾远程连接过该计算机的 IP")
        self.assertIn("Win_RemoteDesktopInfo", jump["command"])
        self.assertNotIn("向日葵", jump["command"])
        self.assertIn("向日葵", jump["forbid"])

    def test_email_photo_is_exif_not_trailer(self):
        jump = dfir_router.route("曾经发送过一张照片，写出 GPS")
        self.assertIn("EXIF", jump["command"])
        self.assertNotIn("trailer", jump["command"])
        self.assertNotIn("ocr", jump["command"].lower())

    def test_unit_price_is_trailer(self):
        jump = dfir_router.route("走私物品的单价是每克多少元")
        self.assertIn("chatpics", jump["command"])
        self.assertIn("docprice", jump["command"])
        self.assertIn("OCR", jump["forbid"])

    def test_serial_uses_device_probe(self):
        jump = dfir_router.route("写出苹果手机的序列号")
        self.assertEqual(jump["skill"], "ios-backup-ctf")
        self.assertIn("ios_backup_probe.py device", jump["command"])
        self.assertIn("机型名", jump["forbid"])

    def test_block_names_index_and_omits_gold(self):
        jump = dfir_router.route("写出嫌疑人最新家庭地址")
        block = dfir_router.format_first_jump_block(jump)
        self.assertIn("device_map.myos.summary.txt", block)
        self.assertNotIn("gold-2024", block)
        self.assertNotIn("state\\eval", block)
        self.assertEqual(dfir_router.format_first_jump_block(dfir_router.route("请做手机取证")), "")

    def test_package_name_uses_apps_probe(self):
        jump = dfir_router.route("该 APP 的包名是什么")
        self.assertIn("ios_backup_probe.py apps", jump["command"])
        self.assertIn("data\\data", jump["forbid"])

    def test_vhd_forbids_hand_parse(self):
        jump = dfir_router.route("计算机中曾挂载的 vhd 非加密分区驱动器号")
        self.assertIn("Mount-Vhd", jump["command"])
        self.assertIn("手解", jump["forbid"])
        self.assertIn("BAT", jump["forbid"])

    def test_sunlogin_beats_rdp(self):
        jump = dfir_router.route("分析向日葵远程连接记录")
        self.assertIn("成功接收到公网", jump["command"])
        self.assertNotIn("Win_RemoteDesktopInfo", jump["command"])

    def test_veracrypt_prefers_emulator_backup(self):
        jump = dfir_router.route("找到 VeraCrypt 加密容器并写出密码")
        self.assertIn(".npbk", jump["command"])
        self.assertIn("破解器", jump["forbid"])

    def test_cli_route_file(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            stem = Path(raw) / "q.txt"
            stem.write_text("曾远程连接过该计算机的 IP", encoding="utf-8")
            proc = subprocess.run([sys.executable, str(Path(dfir_router.__file__)), "--route-file", str(stem)],
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Win_RemoteDesktopInfo", json.loads(proc.stdout)["command"])


if __name__ == "__main__":
    unittest.main()
