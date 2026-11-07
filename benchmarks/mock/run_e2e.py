#!/usr/bin/env python3
"""End-to-end mock test for dfir_general: no model, no real evidence."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = ROOT.parents[1] / "hermes" / "bin"
sys.path.insert(0, str(BIN))
import dfir_general  # noqa: E402


def main() -> int:
    scenarios = {
        1: "success",
        2: "tool_blocked",
        3: "retry_success",
        4: "exhausted",
        5: "budget",
        6: "timeout",
    }
    expected = {
        1: ("OK", 1),
        2: ("TOOL_BLOCKED", 1),
        3: ("OK", 2),
        4: ("EXHAUSTED", 1),
        5: ("BUDGET_EXHAUSTED", 1),
        6: ("TIMEOUT", 1),
    }
    with tempfile.TemporaryDirectory() as td:
        case = Path(td) / "case"
        notes = case / "notes"
        notes.mkdir(parents=True)
        (notes / "case-profile.json").write_text('{"domain":"mobile"}\n', encoding="utf-8")
        (notes / "questions-1-6.txt").write_text(
            "\n".join(f"{i}|mock mobile question {i}?" for i in range(1, 7)) + "\n", encoding="utf-8")
        results = dfir_general.solve_case(case, "1-6", str(notes / "questions-1-6.txt"),
                                          dfir_general.MockAgent(scenarios), skip_pack=True, skip_myos=True)
        failures = []
        for r in results:
            exp_verdict, exp_attempt = expected[r["q"]]
            ok = r["verdict"] == exp_verdict and r["attempt"] == exp_attempt
            print(f"{'OK' if ok else 'FAIL'} Q{r['q']} {r['verdict']} attempt={r['attempt']} expected={exp_verdict}/{exp_attempt}")
            if not ok:
                failures.append(r)
        # A successful pending must be skipped on a rerun, not re-solved.
        rerun = dfir_general.solve_case(case, "1", str(notes / "questions-1-6.txt"),
                                        dfir_general.MockAgent({1: "success"}),
                                        skip_pack=True, skip_myos=True)
        ok_skip = bool(rerun) and rerun[0]["verdict"] == "SKIP_ANSWERED"
        print(f"{'OK' if ok_skip else 'FAIL'} skip answered pending")
        if not ok_skip:
            failures.append("skip")
        # Every non-OK question must leave a pending file.
        for q in (2, 4, 5, 6):
            p = notes / f"pending-{q}.md"
            ok = p.exists() and "答案：" in p.read_text(encoding="utf-8")
            print(f"{'OK' if ok else 'FAIL'} fallback pending Q{q}")
            if not ok:
                failures.append(q)
    print(f"e2e={'PASS' if not failures else 'FAIL'} ({len(results)-len([x for x in failures if isinstance(x,dict)])}/{len(results)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
