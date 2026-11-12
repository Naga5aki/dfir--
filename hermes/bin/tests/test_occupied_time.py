import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import occupied_time


class IdleTest(unittest.TestCase):
    def test_user_gap_over_five_minutes_counts(self):
        self.assertEqual(occupied_time.user_idle_seconds([(0, "assistant"), (301, "user")]), 301)

    def test_tool_gap_does_not_count(self):
        self.assertEqual(occupied_time.user_idle_seconds([(0, "assistant"), (400, "tool")]), 0)

    def test_five_minutes_exact_does_not_count(self):
        self.assertEqual(occupied_time.user_idle_seconds([(0, "assistant"), (300, "user")]), 0)


if __name__ == "__main__":
    unittest.main()
