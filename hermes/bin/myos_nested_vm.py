"""Register a nested VMware VMDK as a MYOS material and mount it read-only.

This is deliberately a separate step from full computer forensics: it calls
add_image_material -> load_case -> query_device_mount_path, and never submits
a re-forensics task. The original VMDK stays read-only.

Safety: live registration requires --yes. Run --dry-run first to see the plan.

Usage:
  python -I myos_nested_vm.py --case-id <id> --vmdk "<...>/我的测试机.vmdk" --dry-run
  python -I myos_nested_vm.py --case-id <id> --vmdk "<...>/我的测试机.vmdk" --yes
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_SERVER = r"D:\MYOS\Client\tools\mcp\myos_mcp_server.exe"


async def call(session, name, args, timeout):
    result = await asyncio.wait_for(session.call_tool(name, args), timeout=timeout)
    texts = [getattr(item, "text", "") for item in (result.content or [])]
    text = next((t for t in texts if t), "")
    if not text:
        return {"_error": f"{name}: empty result", "_isError": getattr(result, "isError", None)}
    try:
        return json.loads(text)
    except Exception:
        return {"_error": f"{name}: non-JSON result", "_prefix": text[:300]}


def find_material_id(obj):
    if isinstance(obj, dict):
        for key in ("materialId", "caseMaterialId", "id"):
            v = obj.get(key)
            if isinstance(v, str) and len(v) >= 8:
                return v
        for v in obj.values():
            found = find_material_id(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_material_id(v)
            if found:
                return found
    return ""


async def run(args):
    vmdk = Path(args.vmdk)
    if not vmdk.exists():
        print(f"VMDK not found: {vmdk}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "caseId": args.case_id,
            "vmdk": str(vmdk),
            "size": vmdk.stat().st_size,
            "materialName": args.name or vmdk.stem,
            "planned": [
                "add_image_material(caseId, imagePaths=vmdk, materialName=name)",
                "load_case(caseId, materialId)",
                "query_device_mount_path(caseId, materialId)",
            ],
        }, ensure_ascii=False, indent=2))
        return 0
    if not args.yes:
        print("refusing live registration without --yes (run --dry-run first)", file=sys.stderr)
        return 2

    params = StdioServerParameters(command=args.server, args=[], env=None)
    out = {"caseId": args.case_id, "vmdk": str(vmdk)}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            add = await call(
                session,
                "myos-forensics.add_image_material",
                {
                    "caseId": args.case_id,
                    "imagePaths": str(vmdk),
                    "materialName": args.name or vmdk.stem,
                },
                args.timeout,
            )
            out["add"] = add
            material_id = find_material_id(add)
            out["materialId"] = material_id
            if material_id:
                load = await call(
                    session,
                    "myos-forensics.load_case",
                    {"caseId": args.case_id, "materialId": material_id},
                    args.timeout,
                )
                out["load"] = load
                mount = await call(
                    session,
                    "myos-forensics.query_device_mount_path",
                    {"caseId": args.case_id, "materialId": material_id},
                    args.timeout,
                )
                out["mount"] = mount
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("materialId") else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--vmdk", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    try:
        return asyncio.run(run(args))
    except Exception as exc:
        print(f"nested VM registration failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
