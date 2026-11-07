# Copy per project. Every root a CLI arg; pending != fail; exit 1 on failure.
import argparse, os, sys, json, hashlib, datetime

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--staging", required=True)
ap.add_argument("--backup", required=True)
ap.add_argument("--round", required=True)
ap.add_argument("--out", default="validator-result.json")
ap.add_argument("--lite", action="store_true")          # probes: skip heavy subprocess checks
ap.add_argument("--allow-pending", action="store_true")  # pre-report run: tolerate not-yet-written inputs
A = ap.parse_args()

FILES = []  # e.g. ["notes-playbooks.md", "notes/notes-summary.md", ...]
res = []


def rec(i, name, ok, detail="", pending=False):
    res.append({"id": i, "check": name, "ok": bool(ok) or pending, "pending": pending,
                "detail": str(detail)[:300]})
    print(("PASS" if ok or pending else "FAIL"), i, name, str(detail)[:140])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


# One try/except block per check; failures are recorded, never raised past the block.
# Heavy checks follow this guard so probe runs stay fast:
#   if A.lite: rec(2, "upstream validator", True, "lite skip", pending=True)
# Bytewise equality:
#   bad = [r for r in FILES if open(os.path.join(A.store, r), "rb").read()
#          != open(os.path.join(A.staging, r), "rb").read()]
#   rec(5, "staging == store (bytewise)", not bad, "bad=%s" % bad)
# Missing artifacts become pending (so --allow-pending pre-runs still exit 0):
#   try: ...
#   except FileNotFoundError:
#       rec(17, "smoke test passed", A.allow_pending, "artifact not yet written", pending=A.allow_pending)

n_fail = sum(1 for r in res if not r["ok"] and not r["pending"])
os.makedirs(os.path.dirname(os.path.abspath(A.out)), exist_ok=True)  # dirname('x.json') == '' without abspath
json.dump({"generated": datetime.datetime.now().isoformat(timespec="seconds"), "checks": res,
           "pass": len(res) - n_fail, "fail": n_fail, "exit_code": 1 if n_fail else 0},
          open(A.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("VALIDATOR: %d/%d PASS, exit=%d" % (len(res) - n_fail, len(res), 1 if n_fail else 0))
sys.exit(1 if n_fail else 0)
