import re
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BIN))
import dfir_plan
import questions_to_pipe


class PipeLinesTest(unittest.TestCase):
    def test_numbered_continuation_joins(self):
        text = "3.去过\n\nA: 甲\n\n4.下一题"
        lines = questions_to_pipe.to_pipe_lines(text)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("3|"))
        self.assertIn("去过", lines[0])
        self.assertIn("A: 甲", lines[0])
        self.assertEqual(lines[1], "4|下一题")

    def test_unnumbered_lines_are_ordered(self):
        text = "第一题\n第二题\n"
        self.assertEqual(questions_to_pipe.to_pipe_lines(text), ["1|第一题", "2|第二题"])

    def test_2024_names_do_not_match_range_autoselect(self):
        name = "questions-2024szb-mobile.txt"
        self.assertIsNone(re.match(r"^questions-(\d+)-(\d+)\.txt$", name))
        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw)
            (notes / "questions-1-8.txt").write_text("1|old\n", encoding="utf-8")
            (notes / "questions-2024szb-mobile.txt").write_text("1|new\n", encoding="utf-8")
            selected = dfir_plan.select_question_file(notes, [1, 2, 8])
            self.assertIsNotNone(selected)
            self.assertEqual(selected.name, "questions-1-8.txt")


if __name__ == "__main__":
    unittest.main()
