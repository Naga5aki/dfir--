"""Query MYOS computer forensics overview once and write a compact index.

The full computer overview is large (dozens of plugin DB entries plus
sqliteQueryHints). This helper keeps only the case/material IDs, the
IntegrateForensics plugin paths and the hints, so a local model can query the
right .mfs without re-reading the raw JSON in chunks.

Read-only: it never writes into the evidence or MYOS case directory.
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

# Question-type shortcuts. Keep this list short; details live in the skill.
TYPE_MAP = [
    ("开关机/最后开机", "Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN（交叉 wtmp/boot.log/syslog）"),
    ("USB", "Linux_UsbInfo / Win_USB"),
    ("微信", "Win_WeChat.mfs（Linux 微信可能无消息表）"),
    ("软件安装/版本", "Linux_InstallSoftWare / Mac_InstallSoftWare / Win_SystemInfo"),
    ("系统信息", "Linux_SystemInfo.mfs"),
    ("浏览器密码/历史", "Any_Chrome / Any_ChromiumBrowser + 钥匙环"),
    ("文档元数据", "Any_OfficeMetaInfo（只有元数据）"),
    ("文件哈希/文件名", "FSData.mfs / MYOS 哈希检索"),
    ("远程控制", "Linux_InstallSoftWare + sunlogin_service.log*"),
]


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


def compact_material(material):
    dbs = material.get("integrateForensicsDatabases") or []
    if not dbs:
        return None
    plugins = []
    for db in dbs:
        if not isinstance(db, dict):
            continue
        plugins.append({
            "pluginName": db.get("pluginName"),
            "dbPath": db.get("dbPath"),
            "schemaXmlExists": db.get("schemaXmlExists"),
            "schemaXmlPath": db.get("schemaXmlPath"),
        })
    hints = []
    for h in material.get("sqliteQueryHints") or []:
        if isinstance(h, dict):
            hints.append({
                "pluginName": h.get("pluginName"),
                "dbPath": h.get("dbPath"),
                "sql": h.get("sql"),
                "maxRows": h.get("maxRows"),
            })
    return {
        "materialDirName": material.get("materialDirName"),
        "materialDir": material.get("materialDir"),
        "mountPath": material.get("mountPath", ""),
        "online": material.get("online"),
        "integrateForensicsDir": material.get("integrateForensicsDir"),
        "hasFSDataMfs": material.get("hasFSDataMfs"),
        "pluginCount": len(plugins),
        "plugins": plugins,
        "sqliteQueryHints": hints,
        "errors": material.get("errors") or [],
    }


def build_summary(compact):
    lines = [
        "MYOS 计算机取证分析结果索引（只读；由 myos_computer_compact.py 生成）",
        f"caseId={compact.get('caseId', '')} caseName={compact.get('caseName', '')}",
        f"generated={compact.get('generated', '')}",
        "",
        "题型速查（先选库，再 sqlite_query；.mfs 只能走 MCP）：",
    ]
    for label, route in TYPE_MAP:
        lines.append(f"- {label}: {route}")
    lines.append("")
    for mat in compact.get("materials") or []:
        lines.append(
            f"检材 {mat.get('materialDirName')} | 插件库={mat.get('pluginCount')} | "
            f"dir={mat.get('materialDir')}"
        )
        if mat.get("mountPath") or mat.get("online") is not None:
            state = mat.get("online")
            if state is None:
                hint = "online=未知（读文件返回 0 字节即视为离线，改走插件库）"
            elif state:
                hint = "online=True"
            else:
                hint = "online=False（原始文件读不出内容，改走插件库）"
            lines.append(f"  mountPath={mat.get('mountPath', '')} {hint}")
        for p in mat.get("plugins") or []:
            schema = "schemaXml=yes" if p.get("schemaXmlExists") else "schemaXml=no"
            lines.append(f"- {p.get('pluginName')} | {p.get('dbPath')} | {schema}")
        if mat.get("errors"):
            lines.append(f"- errors={len(mat.get('errors'))}")
        lines.append("")
    lines.append("使用规则：先按题型选插件库；sqlite_query 查 sqlite_master 一次，再一条有界 SELECT；")
    lines.append("MYOS 插件库没有的正文/图片/嵌套 VM，再走 query_device_mount_path 的原始挂载目录。")
    return "\n".join(lines) + "\n"


async def run(server, notes, case_id):
    params = StdioServerParameters(command=server, args=[], env=None)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            cases = await call(session, "myos-forensics.query_open_cases", {})
            open_cases = cases.get("openCases") or []
            if not open_cases:
                raise RuntimeError("MYOS 没有已打开的案件")
            primary = cases.get("primaryCaseId")
            case = next((c for c in open_cases if c.get("caseId") == primary), open_cases[0])
            cid = case_id or case.get("caseId") or primary
            overview = await call(
                session,
                "myos-forensics.query_computer_forensics_results_overview",
                {"caseId": cid},
            )
            mounts = {}
            for m in overview.get("materials") or []:
                name = m.get("materialDirName")
                if not name:
                    continue
                try:
                    mounts[name] = await call(
                        session,
                        "myos-forensics.query_device_mount_path",
                        {"caseId": cid, "materialName": name},
                    )
                except Exception:
                    mounts[name] = {}

    materials = []
    for m in overview.get("materials") or []:
        cm = compact_material(m)
        if cm:
            mount = mounts.get(m.get("materialDirName"), {})
            cm["mountPath"] = (mount.get("mountPath") or "").replace("\\\\?\\", "")
            cm["online"] = mount.get("deviceOnline", mount.get("online"))
            materials.append(cm)
    compact = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "caseId": overview.get("caseId") or cid,
        "caseName": overview.get("caseName"),
        "caseRootPath": overview.get("caseRootPath"),
        "materials": materials,
        "typeMap": [{"type": k, "route": v} for k, v in TYPE_MAP],
    }
    notes.mkdir(parents=True, exist_ok=True)
    json_path = notes / "device_map.computer.json"
    text_path = notes / "device_map.computer.summary.txt"
    json_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(build_summary(compact), encoding="utf-8")
    print(
        "MYOS computer compact written: materials=%d plugins=%d case=%s"
        % (len(materials), sum(m.get("pluginCount", 0) for m in materials), compact["caseId"])
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", required=True, help="case notes directory")
    parser.add_argument("--case-id", default="", help="optional MYOS case id")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    args = parser.parse_args()
    try:
        asyncio.run(run(args.server, Path(args.notes), args.case_id))
    except Exception as exc:
        print(f"MYOS computer compact failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
