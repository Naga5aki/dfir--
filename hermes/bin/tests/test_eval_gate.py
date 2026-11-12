import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BIN))
import eval_gold

PY = sys.executable


def row(q, verdict, seconds=100, status="OK"):
    return {"question": q, "verdict": verdict, "seconds": seconds, "status": status}


class GoldPathTest(unittest.TestCase):
    def test_gold_inside_notes_is_rejected(self):
        self.assertFalse(eval_gold.gold_path_allowed(Path(r"D:\forensics\cases\notes\gold.json")))
        with tempfile.TemporaryDirectory() as raw:
            gold = Path(raw) / "gold.json"
            gold.write_text(json.dumps({"questions": {"1": {"answer": "SECRET-ANSWER", "accept": ["SECRET-ANSWER"]}}}), encoding="utf-8")
            proc = subprocess.run([PY, str(BIN / "eval_gold.py"), "--gold", str(gold), "--notes", raw], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("SECRET-ANSWER", proc.stdout)


def mobile_summary():
    rows = [row(q, "OK") for q in (1, 3, 4, 5, 6, 7, 8)] + [row(2, "UNKNOWN")]
    return {"rows": rows, "wrong": 0, "elapsed_seconds": 800}


class GateTest(unittest.TestCase):
    def test_wrong_is_not_unknown(self):
        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw)
            (notes / "pending-1.md").write_text("答案：1200元\n", encoding="utf-8")
            summary = {"rows": [row(1, "WRONG")], "wrong": 1, "elapsed_seconds": 100}
            fails = eval_gold.paper_gate(summary, "mobile")
            self.assertTrue(any("WRONG" in f for f in fails))
            self.assertFalse(any("UNKNOWN" in f and "1" in f for f in fails))

    def test_mobile_gate_numbers(self):
        self.assertEqual(eval_gold.paper_gate(mobile_summary(), "mobile"), [])
        bad = mobile_summary()
        bad["rows"] = [r if r["question"] != 3 else row(3, "UNKNOWN") for r in bad["rows"]]
        self.assertTrue(eval_gold.paper_gate(bad, "mobile"))

    def test_computer_q3_unknown_allowed(self):
        rows = [row(q, "OK") for q in (1, 2, 6, 7, 8, 9, 10)] + [row(q, "UNKNOWN") for q in (3, 4, 5)]
        summary = {"rows": rows, "wrong": 0, "elapsed_seconds": 1000}
        self.assertEqual(eval_gold.paper_gate(summary, "computer"), [])
        bad = {"rows": [r if r["question"] != 6 else row(6, "WRONG") for r in rows], "wrong": 1, "elapsed_seconds": 1000}
        self.assertTrue(eval_gold.paper_gate(bad, "computer"))


if __name__ == "__main__":
    unittest.main()
