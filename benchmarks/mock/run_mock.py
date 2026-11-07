#!/usr/bin/env python3
"""Deterministic mock benchmark for the case-agnostic DFIR planner.

It does not call a model and does not read real case evidence. It verifies:
  * domain/task/profile/tier decisions across mobile/PC/network/memory/reverse;
  * case-profile and sidecar overrides;
  * question-file range selection;
  * success/skip/retry classification from pending text.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = ROOT.parents[1] / "hermes" / "bin"
sys.path.insert(0, str(BIN))
import dfir_plan  # noqa: E402


def tier(plan):
    return "deep" if plan.deep else "complex" if plan.complex else "base"


def check(rows):
    failures = []
    results = []
    for item in rows:
        notes = ROOT / "cases" / item["case"] / "notes"
        plan = dfir_plan.build_plan(item["q"], item["text"], notes)
        exp = item["expected"]
        actual = {"domain": plan.domain, "task": plan.task, "profile": plan.profile, "tier": tier(plan)}
        ok = actual == exp
        results.append({"q": item["q"], "case": item["case"], "ok": ok, "expected": exp, "actual": actual, "score": plan.score})
        if not ok:
            failures.append(results[-1])
    return results, failures


def check_pending():
    cases = [
        ("答案：TEST-VALUE\n证据：mock\n已排除：无\n下一轮：完成", "OK", False),
        ("答案：UNKNOWN\n证据：已定位表\n已排除：候选A\n下一轮：完成", "EXHAUSTED", False),
        ("答案：UNKNOWN\n证据：已定位表\n已排除：候选A\n下一轮：查候选B", "UNKNOWN", True),
        ("证据：没有答案行\n已排除：无\n下一轮：继续", "NO_ANSWER", True),
    ]
    failures = []
    results = []
    for text, status, has_next in cases:
        got = dfir_plan.evaluate_pending(text)
        ok = got["status"] == status and got["has_next"] == has_next
        results.append({"text": text.splitlines()[0], "ok": ok, "expected": status, "actual": got["status"], "has_next": got["has_next"]})
        if not ok:
            failures.append(results[-1])
    return results, failures


def check_overrides():
    failures = []
    results = []
    with tempfile.TemporaryDirectory() as td:
        notes = Path(td) / "notes"
        notes.mkdir()
        (notes / "questions-1-8.txt").write_text("1|q1\n2|q2\n8|q8\n", encoding="utf-8")
        (notes / "questions-15-20.txt").write_text("15|q15\n20|q20\n", encoding="utf-8")
        (notes / "complex-questions.txt").write_text("2\n", encoding="utf-8")
        (notes / "deep-questions.txt").write_text("8\n", encoding="utf-8")
        sel = dfir_plan.select_question_file(notes, [1, 2, 8])
        ok_sel = sel is not None and sel.name == "questions-1-8.txt"
        results.append({"check": "question-file-range", "ok": ok_sel, "actual": sel.name if sel else None})
        if not ok_sel:
            failures.append(results[-1])
        p2 = dfir_plan.build_plan(2, "一个没有类型关键词的问题", notes)
        p8 = dfir_plan.build_plan(8, "另一个没有类型关键词的问题", notes)
        ok_ov = p2.complex and not p2.deep and p8.deep and p8.profile == "dfir-max"
        results.append({"check": "complex/deep sidecar", "ok": ok_ov, "q2": tier(p2), "q8": tier(p8), "q8_profile": p8.profile})
        if not ok_ov:
            failures.append(results[-1])
        (notes / "case-profile.json").write_text(
            '{"domain":"generic","profile":"dfir-max","skills":["utm-forensic-cli"],"budgets":{"base":{"turns":9,"seconds":300}}}',
            encoding="utf-8")
        p9 = dfir_plan.build_plan(9, "一个普通定位问题是什么？", notes)
        ok_case = p9.profile == "dfir-max" and p9.turns == 9 and p9.budget_seconds == 300 and p9.skills == ["utm-forensic-cli"]
        results.append({"check": "case-profile override", "ok": ok_case, "profile": p9.profile, "turns": p9.turns, "seconds": p9.budget_seconds})
        if not ok_case:
            failures.append(results[-1])
    return results, failures


def check_routes(rows):
    failures = []
    results = []
    profiles = ROOT.parents[1] / "hermes" / "profiles"
    for item in rows:
        notes = ROOT / "cases" / item["case"] / "notes"
        plan = dfir_plan.build_plan(item["q"], item["text"], notes)
        cfg = profiles / plan.profile / "config.yaml"
        cfg_ok = cfg.exists() and "provider: local" in cfg.read_text(encoding="utf-8")
        skills_ok = True
        missing = []
        for skill in plan.skills:
            candidates = [profiles / plan.profile / "skills" / skill / "SKILL.md",
                          profiles / plan.profile / "skills" / "forensics" / skill / "SKILL.md",
                          profiles / plan.profile / "skills" / "security" / skill / "SKILL.md"]
            if not any(c.exists() for c in candidates):
                skills_ok = False
                missing.append(skill)
        ok = cfg_ok and skills_ok
        results.append({"q": item["q"], "profile": plan.profile, "config": cfg_ok, "skills": plan.skills, "missing": missing, "ok": ok})
        if not ok:
            failures.append(results[-1])
    return results, failures


def main():
    rows = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    r1, f1 = check(rows)
    r2, f2 = check_pending()
    r3, f3 = check_overrides()
    r4, f4 = check_routes(rows)
    failures = f1 + f2 + f3 + f4
    report = {
        "planner": {"total": len(r1), "passed": len(r1) - len(f1), "failures": f1, "results": r1},
        "pending": {"total": len(r2), "passed": len(r2) - len(f2), "failures": f2, "results": r2},
        "overrides": {"total": len(r3), "passed": len(r3) - len(f3), "failures": f3, "results": r3},
        "routes": {"total": len(r4), "passed": len(r4) - len(f4), "failures": f4, "results": r4},
        "ok": not failures,
    }
    (ROOT / "last_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in r1:
        print(f"{'OK' if item['ok'] else 'FAIL'} q={item['q']:>2} {item['case']:<7} expected={item['expected']} actual={item['actual']} score={item['score']}")
    for item in r2:
        print(f"{'OK' if item['ok'] else 'FAIL'} pending {item['expected']} -> {item['actual']} next={item['has_next']}")
    for item in r3:
        print(f"{'OK' if item['ok'] else 'FAIL'} {item['check']}: {item}")
    for item in r4:
        print(f"{'OK' if item['ok'] else 'FAIL'} route q={item['q']} profile={item['profile']} config={item['config']} missing={item['missing']}")
    print(f"planner={len(r1)-len(f1)}/{len(r1)} pending={len(r2)-len(f2)}/{len(r2)} overrides={len(r3)-len(f3)}/{len(r3)} routes={len(r4)-len(f4)}/{len(r4)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
