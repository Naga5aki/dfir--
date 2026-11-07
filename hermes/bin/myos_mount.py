#!/usr/bin/env python3
"""MYOS 挂载/卸载自动化（静默）。

用法：
  python myos_mount.py mount [--case 案件名] [--material 检材名] [--wait 180]
  python myos_mount.py unmount
  python myos_mount.py status

行为：
  - 已有挂载（例如 Myos 桌面已打开案件）→ 直接复用，不重复挂载、不在退出时卸载；
  - 由本脚本挂载 → 记录状态，unmount 时通过 close_case 卸载；
  - 状态写入 STATE_FILE，供 Hermes 会话直接读取，避免模型反复探测路径。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXE = r"D:\MYOS\Client\tools\mcp\myos_mcp_server.exe"
STATE_DIR = Path(r"D:\ForensicsAgent\hermes\state")
STATE_FILE = STATE_DIR / "myos_mount.json"
LOG_FILE = Path(r"D:\ForensicsAgent\hermes\logs\myos_mount.log")


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


class Myos:
    def __init__(self) -> None:
        self.p = subprocess.Popen(
            [EXE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._id = 0
        self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hermes-mount", "version": "1.0"},
        })
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        self.p.stdin.flush()

    def _call(self, method: str, params=None, timeout: int = 120):
        self._id += 1
        mid = self._id
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method,
                                       "params": params or {}}, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self.p.stdout.readline()
            if not line:
                return {"error": "eof"}
            try:
                obj = json.loads(line.strip())
            except Exception:
                continue
            if obj.get("id") == mid:
                return obj
        return {"error": "timeout"}

    def tool(self, name: str, args: dict, timeout: int = 180):
        r = self._call("tools/call", {"name": name, "arguments": args}, timeout=timeout)
        res = r.get("result") or {}
        txt = "".join(c.get("text", "") for c in (res.get("content") or []) if c.get("type") == "text")
        if not txt:
            return {"error": json.dumps(r, ensure_ascii=False)}
        try:
            return json.loads(txt)
        except Exception:
            return {"raw": txt}

    def close(self) -> None:
        try:
            self.p.terminate()
            self.p.wait(timeout=5)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def norm(p: str) -> Path:
    r"""把 \\?\C:\... 形式还原成普通路径。"""
    if not p:
        return Path("")
    if p.startswith("\\\\?\\"):
        p = p[4:]
    return Path(p)


def usable_root(mount_path: str) -> Path:
    """tar 类检材挂载后多一层 userdata；磁盘镜像则直接是根。"""
    base = norm(mount_path)
    sub = base / "userdata"
    try:
        if sub.is_dir():
            return sub
    except Exception:
        pass
    return base


def readable(p: Path) -> bool:
    try:
        return p.is_dir() and any(p.iterdir())
    except Exception:
        return False


def pick_case(api: Myos, wanted: str):
    data = api.tool("myos-forensics.query_open_cases", {})
    cases = [c for c in (data.get("openCases") or []) if c.get("isOpen")]
    if wanted:
        for c in cases:
            if wanted.lower() in (c.get("caseName") or "").lower():
                return c
    return cases[0] if cases else None


def pick_material(api: Myos, case_id: str, wanted: str):
    data = api.tool("myos-forensics.query_materials", {"caseId": case_id, "statusOnly": True})
    mats = [m for m in (data.get("materials") or []) if m.get("isSuccess", True)]
    if wanted:
        for m in mats:
            if wanted.lower() in (m.get("name") or "").lower():
                return m
        return None
    # 手机取证优先逻辑镜像（typeCode 07 / userdata 命名）
    for m in mats:
        if (m.get("typeCode") == "07") or ("userdata" in (m.get("name") or "").lower()):
            return m
    return mats[0] if mats else None


def load_state():
    try:
        if STATE_FILE.is_file():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def save_state(state) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def do_mount(case_name: str, material_name: str, wait: int, silent: bool = False) -> int:
    api = Myos()
    try:
        case = pick_case(api, case_name)
        if not case:
            log("mount: no open case")
            return 2
        case_id = case["caseId"]
        mat = pick_material(api, case_id, material_name)
        if not mat:
            log("mount: material not found")
            return 3
        mat_id = mat["materialId"]

        state = {
            "caseId": case_id,
            "caseName": case.get("caseName"),
            "materialId": mat_id,
            "materialName": mat.get("name"),
            "mountedByUs": False,
            "mountedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        info = api.tool("myos-forensics.query_device_mount_path", {"materialId": mat_id})
        mount_path = info.get("mountPath") or info.get("dokanPath") or ""
        root = usable_root(mount_path) if mount_path else Path("")

        if mount_path and readable(root):
            state["mountPath"] = mount_path
            state["rootPath"] = str(root)
            # 上次本工具挂载后异常退出留下的残留：接管，退出时由我们清理
            prev = load_state()
            if prev and prev.get("mountedByUs") and prev.get("caseId") == case_id \
                    and prev.get("materialId") == mat_id:
                state["shared"] = False
                state["mountedByUs"] = True
                log("mount: adopted leftover mount %s" % root)
            else:
                state["shared"] = True
                log("mount: reused existing mount %s" % root)
            save_state(state)
            return 0

        api.tool("myos-forensics.load_case", {"caseId": case_id, "materialId": mat_id}, timeout=300)
        deadline = time.time() + wait
        while time.time() < deadline:
            info = api.tool("myos-forensics.query_device_mount_path", {"materialId": mat_id})
            mount_path = info.get("mountPath") or info.get("dokanPath") or ""
            if mount_path:
                root = usable_root(mount_path)
                if readable(root):
                    state.update({
                        "mountPath": mount_path,
                        "rootPath": str(root),
                        "shared": False,
                        "mountedByUs": True,
                    })
                    save_state(state)
                    log("mount: mounted by us %s" % root)
                    return 0
            time.sleep(2)
        log("mount: timeout waiting for mount path")
        return 4
    finally:
        api.close()


def do_unmount(silent: bool = False) -> int:
    if not STATE_FILE.is_file():
        return 0
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        STATE_FILE.unlink(missing_ok=True)
        return 0
    if not state.get("mountedByUs"):
        STATE_FILE.unlink(missing_ok=True)
        log("unmount: shared mount, left as-is")
        return 0
    api = Myos()
    try:
        api.tool("myos-forensics.close_case", {"caseId": state["caseId"]}, timeout=180)
        log("unmount: closed case %s" % state.get("caseName"))
    finally:
        api.close()
        STATE_FILE.unlink(missing_ok=True)
    return 0


def do_status() -> int:
    if STATE_FILE.is_file():
        print(STATE_FILE.read_text(encoding="utf-8"))
    else:
        print("not mounted by hermes")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print("usage: myos_mount.py mount|unmount|status", file=sys.stderr)
        return 1
    cmd = argv[0]
    def opt(name, default=""):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                return argv[i + 1]
        return default
    if cmd == "mount":
        case_name = os.getenv("MYOS_CASE", "") or opt("--case", "")
        material_name = os.getenv("MYOS_MATERIAL", "") or opt("--material", "")
        wait = int(opt("--wait", "180"))
        return do_mount(case_name, material_name, wait, silent=True)
    if cmd == "unmount":
        return do_unmount(silent=True)
    if cmd == "status":
        return do_status()
    print("unknown command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
