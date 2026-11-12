"""Query MYOS MCP once and write a compact, question-neutral analysis index.

The full phone overview can be hundreds of KB. This helper keeps only the
case/material IDs, counts, app-level .mfs paths and sqliteQueryHints so the
solver can query MYOS's parsed results without dumping raw JSON into context.
It never reads or writes answer files.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_SERVER = r"D:\MYOS\Client\tools\mcp\myos_mcp_server.exe"


async def call(session, name, args):
    result = await session.call_tool(name, args)
    texts = [getattr(item, "text", "") for item in (result.content or [])]
    text = next((t for t in texts if t), "")
    if not text:
        return {"_error": f"{name}: empty result", "_isError": getattr(result, "isError", None)}
    try:
        return json.loads(text)
    except Exception:
        return {"_error": f"{name}: non-JSON result", "_prefix": text[:200]}


def compact_apps(overview):
    stats = overview.get("mfsStats") or {}
    apps = []
    for app in stats.get("apps") or []:
        if not isinstance(app, dict):
            continue
        apps.append({
            "displayNameZh": app.get("displayNameZh"),
            "strAppName": app.get("strAppName"),
            "dwAppDataCount": app.get("dwAppDataCount"),
            "emAppType": app.get("emAppType"),
            "appMfsPath": app.get("appMfsPath"),
            "strAppFileName": app.get("strAppFileName"),
        })
    return {
        "appCount": stats.get("appCount"),
        "totalAppDataCount": stats.get("totalAppDataCount"),
        "indexTable": stats.get("indexTable"),
        "mappsDbPath": stats.get("mappsDbPath"),
        "apps": apps,
    }


def compact_errors(overview):
    out = []
    for err in overview.get("errors") or []:
        if isinstance(err, dict):
            out.append({"code": err.get("code"), "message": str(err.get("message", ""))[:300]})
        else:
            out.append({"message": str(err)[:300]})
    return out


def build_summary(compact):
    lines = [
        "MYOS 手机取证分析结果索引（只读；由 myos_compact.py 生成）",
        f"caseMaterialId={compact.get('caseMaterialId', '')}",
        f"materialName={compact.get('materialName', '')}",
        f"analysisMode={(compact.get('overview') or {}).get('analysisMode', '')}",
        f"App={compact.get('mfsStats', {}).get('appCount')} 数据项={compact.get('mfsStats', {}).get('totalAppDataCount')} "
        f"取证结果={compact.get('summary', {}).get('forensicResultCount')} 文件={compact.get('summary', {}).get('evidenceFileCount')}",
        "",
        "已解析 App（优先 sqlite_query appMfsPath；不要重复枚举）：",
    ]
    for app in compact.get("mfsStats", {}).get("apps", []):
        if (app.get("dwAppDataCount") or 0) <= 0:
            continue
        lines.append(f"- {app.get('displayNameZh') or app.get('strAppName')} | 数据项={app.get('dwAppDataCount')} | {app.get('appMfsPath')}")
    lines.append("")
    hints = compact.get("sqliteQueryHints") or []
    if hints:
        lines.append("sqliteQueryHints：")
        for h in hints:
            lines.append(f"- {h.get('tool')} | {h.get('dbPath')}")
            if h.get("sql"):
                lines.append(f"  SQL: {h.get('sql')}")
    lines.append("")
    lines.append("使用规则：MYOS 已解析的 App/微信题先用 sqlite_query 查上面的 appMfsPath；")
    lines.append("notes/realm/图片 OCR 等 MYOS 未解析的源，再走原始挂载目录或证据包。")
    return "\n".join(lines) + "\n"


async def run(server, notes, case_id_arg="", material_id_arg=""):
    params = StdioServerParameters(command=server, args=[], env=None)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            cases = await call(session, "myos-forensics.query_open_cases", {})
            open_cases = cases.get("openCases") or []
            if not open_cases:
                raise RuntimeError("MYOS 没有已打开的案件")
            if case_id_arg:
                case = next((c for c in open_cases if c.get("caseId") == case_id_arg), None)
                if case is None:
                    raise RuntimeError(f"指定案件未打开: {case_id_arg}")
            else:
                primary = cases.get("primaryCaseId")
                case = next((c for c in open_cases if c.get("caseId") == primary), open_cases[0])
            case_id = case.get("caseId")
            materials = await call(session, "myos-forensics.query_materials", {"caseId": case_id})
            mats = materials.get("materials") or []
            if not mats:
                raise RuntimeError("案件没有检材")
            finished = [m for m in mats if str(m.get("frscStatusName", "")).lower() in ("finished", "完成")]
            if material_id_arg:
                material = next((m for m in mats if material_id_arg in (m.get("materialId"), m.get("caseMaterialId"))), None)
                if material is None:
                    raise RuntimeError(f"指定检材不在案件中: {material_id_arg}")
            else:
                material = (finished or mats)[0]
            material_id = material.get("materialId") or material.get("caseMaterialId")
            summary = await call(session, "myos-forensics.query_phone_file_forensics_result_summary", {"caseMaterialId": material_id})
            overview = await call(session, "myos-forensics.query_phone_forensics_results_overview", {"caseMaterialId": material_id})

    compact = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "caseId": case_id,
        "caseMaterialId": material_id,
        "materialName": overview.get("materialName") or material.get("materialName") or material.get("name"),
        "materialDir": overview.get("materialDir"),
        "summary": summary,
        "overview": {
            "analysisMode": (overview.get("overview") or {}).get("analysisMode"),
            "appCount": (overview.get("overview") or {}).get("appCount"),
            "totalAppDataCount": (overview.get("overview") or {}).get("totalAppDataCount"),
            "evidenceFileCount": overview.get("evidenceFileCount"),
            "forensicResultCount": overview.get("forensicResultCount"),
            "resultClassCounts": overview.get("resultClassCounts"),
        },
        "mfsStats": compact_apps(overview),
        "sqliteQueryHints": overview.get("sqliteQueryHints") or [],
        "errors": compact_errors(overview),
    }
    notes.mkdir(parents=True, exist_ok=True)
    json_path = notes / "device_map.myos.json"
    text_path = notes / "device_map.myos.summary.txt"
    json_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(build_summary(compact), encoding="utf-8")
    print(f"MYOS compact written: apps={compact['mfsStats'].get('appCount')} "
          f"data={compact['mfsStats'].get('totalAppDataCount')} "
          f"hints={len(compact['sqliteQueryHints'])} material={material_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", required=True, help="case notes directory")
    parser.add_argument("--case-id", default="", help="open case to index; default is the primary case")
    parser.add_argument("--material-id", default="", help="material to index; default is the first finished one")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    args = parser.parse_args()
    try:
        asyncio.run(run(args.server, Path(args.notes), args.case_id, args.material_id))
    except Exception as exc:
        print(f"MYOS compact failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
