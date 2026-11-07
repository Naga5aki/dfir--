# Copy per project. Backup → temp+fsync+os.replace → read-back → apply/rollback records.
import os, shutil, hashlib, json, datetime


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def promote(files, store_root, staging_root, backup_root, round_dir):
    """files: relative paths present in staging (and possibly new in the store)."""
    os.makedirs(backup_root, exist_ok=True)
    records = []
    for rel in files:
        src, dst = os.path.join(staging_root, rel), os.path.join(store_root, rel)
        bkp = os.path.join(backup_root, rel)
        os.makedirs(os.path.dirname(bkp), exist_ok=True)
        if os.path.exists(dst):
            shutil.copy2(dst, bkp)
            pre = sha(bkp)
        else:
            pre = "ABSENT-PRE-PROMOTION"  # new file this round; rollback = delete it
        data = open(src, "rb").read()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + ".promo-tmp"  # same directory ⇒ same volume ⇒ atomic replace
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dst)
        back = open(dst, "rb").read()
        records.append({"file": rel, "pre_hash": pre,
                        "staging_hash": hashlib.sha256(data).hexdigest(),
                        "post_hash": hashlib.sha256(back).hexdigest(),
                        "bytes_equal_to_staging": back == data, "abs_path": dst})
    fails = [r["file"] for r in records if not r["bytes_equal_to_staging"]]
    json.dump({"generated": datetime.datetime.now().isoformat(timespec="seconds"),
               "records": records, "fail": fails},
              open(os.path.join(round_dir, "apply-record.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"restore": [{"file": r["file"], "from": os.path.join(backup_root, r["file"]),
                             "expected_hash": r["pre_hash"]} for r in records],
               "verify": "re-hash restored files against expected_hash; delete files recorded ABSENT-PRE-PROMOTION"},
              open(os.path.join(round_dir, "rollback-record.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    assert not fails, "read-back mismatch: stop, roll back from backup, rebuild, re-apply"
