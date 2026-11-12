import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ios_backup_probe

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16 + b"IEND" + b"\x00\x00\x00\x00"
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16


def make_backup(root: Path):
    wx = root / "private/var/mobile/Containers/Data/Application/com.tencent.xin/Documents/abc123"
    img = wx / "Img" / "convhash01"
    img.mkdir(parents=True)
    (img / "19.pic").write_bytes(PNG + OLE)
    (img / "20.pic").write_bytes(PNG)  # no trailer, must be skipped
    dbdir = wx / "DB"
    dbdir.mkdir()
    con = sqlite3.connect(dbdir / "message_3.sqlite")
    con.execute("CREATE TABLE Chat_convhash01 (CreateTime INTEGER, Message TEXT)")
    con.executemany("INSERT INTO Chat_convhash01 VALUES (?, ?)", [
        (1, "你把这批货价格发我下"),
        (2, "mm20241105"),
    ])
    con.commit()
    con.close()


class ChatImageTest(unittest.TestCase):
    def test_finds_image_with_ole_trailer(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            make_backup(root)
            found = ios_backup_probe.find_chat_image(root, "convhash01")
            self.assertEqual(found.name, "19.pic")

    def test_returns_none_when_no_trailer(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            make_backup(root)
            self.assertIsNone(ios_backup_probe.find_chat_image(root, "nosuchconv"))

    def test_password_from_chat_table(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            make_backup(root)
            db = root / "private/var/mobile/Containers/Data/Application/com.tencent.xin/Documents/abc123/DB/message_3.sqlite"
            self.assertEqual(ios_backup_probe.chat_password(str(db), "Chat_convhash01"), "mm20241105")


if __name__ == "__main__":
    unittest.main()
