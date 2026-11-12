r"""Fake hermes for dfir-solve tests: writes an evidence-backed UNKNOWN pending.

ASCII-only source: the Chinese labels are escapes so no console encoding
can corrupt them.
"""
import re
import sys
from pathlib import Path

args = sys.argv[1:]
prompt = None
for i, arg in enumerate(args):
    if arg == "--query-file" and i + 1 < len(args):
        prompt = args[i + 1]
if not prompt:
    sys.exit(1)
match = re.search(r"_solve-q(\d+)\.prompt\.txt$", Path(prompt).name)
if not match:
    sys.exit(1)
q = match.group(1)
notes = Path(prompt).parent
body = [
    "题" + q + "（fake）",
    "答案：UNKNOWN",
    "证据：fake hermes 未取到",
    "已排除：假工具路径",
    "下一轮：换分支",
]
(notes / f"pending-{q}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
sys.exit(0)
