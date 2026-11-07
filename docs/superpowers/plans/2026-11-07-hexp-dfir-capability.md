# DFIR hexp 能力沉淀 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 8 个 `.hexp` 专家包里能在本机跑通的取证纪律，沉淀进已有 `dfir*` 技能和路由器，让本地模型优先读 MYOS 已有结果、只对缺口补一条有界查询，并修正当前把内存/流量/逆向题路由到已禁用技能的问题。

**Architecture:** Hermes 不加载独立的 `skill-library` 目录。技能是否进上下文，只看 `profiles/<profile>/skills/<category>/<name>/SKILL.md` 是否存在，以及该名字是否在 `config.yaml` 的 `skills.disabled` 里。启动时只注入技能名和 description；正文靠 `skill_view` 按需读取。因此本方案不新建一套永远挂载的专家库，而是改已有技能、只在缺口处新增两个按需技能，并把 `dfir_plan.py` / `dfir_router.py` 指到真实存在且已启用的技能。MYOS 二次分析只改 `dfir-myos` 与 `dfir-max` 上那份已有的 `myos-results-analysis`。

**Tech Stack:** Hermes profiles、YAML `skills.disabled`、`pre_llm_call` 钩子 `dfir_router.py`、解题入口 `dfir_plan.py`、MYOS MCP `myos_mcp_server.exe`（工具白名单已写在 config，不改）、Python 3.14 标准库测试。无新依赖。

**Spec:** `D:\Desktop\DFIR-hexp能力沉淀实施方案-2026-11-07.md`（同文副本在 `reports\DFIR-hexp能力沉淀实施方案-2026-11-07.md`）。两文冲突时以本计划为准。本计划吸收其备份、不改模型、不重包 MCP、不导入攻击步骤、长模板不进 SOUL、无回执即待核实；并修正其与运行时不符的部分。

## Global Constraints

- 不改模型名、`http://127.0.0.1:8095/v1`、`D:/llm/ensure_local_ready.py`、钩子注册行、端口 `8737` / `8765` / `17621`。
- 不移动、不重包装、不改名 `D:/MYOS/Client/tools/mcp/myos_mcp_server.exe`。不增删 `mcp_servers.*.tools.include`。
- 不覆盖这些备份：`hermes\profiles\.backup-20261031-computer`、`.backup-20261031-skill-prune`、`.backup-20261101-keyword-framework`，以及任何 `config.yaml.bak-didctf-*`。
- 本目录不是 git 仓库。每任务的检查点是把该任务要改的文件再复制进 `hermes\profiles\.backup-20261107-hexp-import\checkpoints\task-N\`，不执行 `git commit`。
- `memory.memory_enabled` 与 `user_profile_enabled` 在六个 profile 都是 `false`。Hermes 因此不把 `memories\MEMORY.md` 注入系统提示。本计划不打开这两个开关，不新建 memory 文件。决策规则写入会被 `skill_view` 读到的技能，或写入已经常驻的 SOUL 的一行替换。
- 不把 hexp 全文贴进 SOUL。`dfir-myos` / `dfir-max` 的 SOUL 只允许替换一个不存在的工具名，净增不超过 200 字节。
- 技能 description 保持一行，不超过 120 个字符。超过约 8 KB 的新正文放 `references/`，不放 SKILL.md 前部以外的地方；已有长技能不整篇重写。
- 工具名以当前会话 `tool_search` 返回的精确名为准，含 `_<hash8>` 后缀。技能里只写短名，并写明禁止把短名直接当调用名。
- 下列产品工具本机不存在，技能正文不得把它们写成可调用步骤：`ges status`、`ges case`、`ges read`、`ges ls`、`Goldeneyes://`、`thunder-app-`、`survey_binary`、`ida_pro_mcp`、`x64dbg` 的 `SetBreakpoint` / `LoadBinary`、`create-vm`、`clonezilla-to-e01`、`pywmxclient`、WMX CLI。允许出现的唯一句式是“未接入，不要调用”。
- 不导入头像、空目录、traffic 包里嵌套的那份与桌面账单包字节相同的 zip（SHA-256 `7d90c7ff6694d810fec7a38f9ecda042ee8e8c111446e687436eed5c689d36cf`）。
- 不导入反调试补丁、绕过、dump 后执行、恶意行为复现步骤。
- 赛题提交口径“成功接收到公网”可留在现有计算机解题技能里；不得写入笔录技能或笔录模板。
- 解题输出先写答案。`E1`/`E2`/`E3`/`E4` 和“已确认/高度支持/初步支持/线索提示/待验证”只允许出现在证据栏或用户明确要求的报告里，技能必须写明不得把这些等级词当作 DIDCTF 提交值。
- 同一 `.mfs` 查询分支两次零命中就换表或停止。第三次扩大同一查询视为失败。
- 不运行 `md_to_gongwen_docx.py`。不 `pip install`。不跑真实 MYOS 案件。
- 测试不依赖 pytest。唯一命令是 `python -I hermes/bin/tests/test_hexp_routing.py`。测试文件用 `unittest`，底部调用 `unittest.main()`。

## Review Focus

- 计算机题被分到没有 MYOS MCP 的 `dfir`，或内存/流量/逆向题仍分到已禁用的 `utm-forensic-cli`：解题人会先空转数轮。对应测试在 Task 2。
- 技能正文出现 `ges`、`thunder-app`、`survey_binary`、`pywmxclient` 或把 `create-vm` 写成操作步骤：本地模型会调用不存在的工具。对应测试在 Task 3、Task 6、Task 7、Task 8 和 Task 10。
- 笔录技能或模板含“成功接收到公网”：赛题口径会写进文书。对应测试在 Task 8。
- 四个无 MYOS 的 profile 被写上完整 `sqlite_query` 流程，或 `dfir-myos` 的 9765 字节技能被短副本覆盖：要么幻觉调用，要么丢掉已验证的计算机快路径。对应测试在 Task 3。
- 卡片把 `query_phone_file_forensics_result_summary` 写成可调用工具：该名字不在白名单，会白耗一轮。对应测试在 Task 3 和 Task 4。

## 与 Codex 方案的取舍

保留：

- 不改模型、端口、MYOS 可执行文件。
- 先备份，且备份目录不覆盖 2026-10-31 / 2026-11-01 的旧备份。
- 证据无回执不得升格；长模板进 references；`dfir-max` 不挂全部深挖正文。
- 嵌套 wmx zip 只导入一次；头像不沉淀。
- EXE 包只留观察点和交接，不留绕过步骤。
- 仿真不等于对原检材已执行。

修正（这些是本计划相对 Codex 方案的决定，不是待确认项）：

- 技能注册方式已经核实：目录名即技能名；`skills.disabled` 是排除名单，没有 `enabled` 列表。不需要再做一轮“只读确认注册”。
- `myos-results-analysis` 已存在。`dfir-myos` 与 `dfir-max` 是 9765 字节的计算机快路径版；其余四个 profile 是 3668 字节旧版。禁止广播覆盖。
- `hermes\skill-library\hexp-import-20261107\` 不会被 Hermes 加载。库只作源副本和漂移检查，运行副本必须在 profile 的 `skills/` 下。
- Codex 写的备份路径 `D:\ForensicsAgent\profiles\.backup-...` 是错的。正确根是 `D:\ForensicsAgent\hermes\profiles\`。
- `MEMORY.md` 当前不进提示词。打开 `memory_enabled` 会把整份 memory 打进每轮 prefill，并与 SOUL 里已有的计算机纪律重复。本计划不打开它。
- GoldenEyes 包写的是 `ges` CLI 和 `Goldeneyes://` 角标。本机二次分析工具是下面这份白名单。导入时翻译，不照抄命令。
- `dfir_plan.py` 现在把 network / memory / reverse 的技能设成已禁用的 `utm-forensic-cli`。这比缺一份新技能更伤速度。允许改这两个 Python 文件的路由表；不允许改钩子注册和模型 URL。
- 不新建 11 个常驻技能。只新增 `bill-flow-analysis` 和 `forensic-record-draft`。其余 hexp 内容并入已有技能的短节或 references。

## 运行时事实（实施时不要重新发现）

六个 profile 都是 `qwen3.8-27b-forensics`，`context_length: 65536`，`base_url: http://127.0.0.1:8095/v1`。`pre_llm_call` 都调用 `dfir_router.py`。

| Profile | 有 MYOS MCP | 其他取证 MCP | 富技能（仅这两个 profile 有长版） |
|---|---|---|---|
| `dfir` | 否 | `case_fs` | 无 |
| `dfir-max` | 是 | didctf、ida `8737`、jadx、wiremcp、memforensics、lovelyspark `8765`、lovelymem `17621`、case_fs | `myos-results-analysis`、`linux-loader`、`windows-loader`、`android-app-forensics` |
| `dfir-mem` | 否 | memforensics、lovelymem `17621`、case_fs | 无 |
| `dfir-myos` | 是 | didctf、case_fs 无；MYOS 白名单与 max 相同 | 同上 |
| `dfir-pcap` | 否 | wiremcp、lovelyspark `8765`、case_fs | 无 |
| `dfir-re` | 否 | ida 六工具、jadx、case_fs | 无 |

MYOS 白名单短名（config 里带 `myos-forensics.` 前缀；调用名还要加会话哈希后缀）：

`health_check_dbus`、`query_cases`、`query_open_cases`、`open_case`、`query_materials`、`load_case`、`add_image_material`、`add_disk_material`、`add_file_collection_material`、`query_computer_forensics_results_overview`、`query_device_info`、`query_device_mount_path`、`query_current_node_data`、`quick_search_files`、`sqlite_query`、`create_file_index_task`、`quick_search_content`、`global_search_content`、`query_task_status`、`wait_task_completion`、`query_phone_forensics_results_overview`、`query_encrypt_types`、`decrypt_partition`、`query_decrypt_task_status`、`restart_computer_forensics`。

不在白名单、但现有 SOUL 写了的名字：`query_phone_file_forensics_result_summary`。Task 4 删掉它。

IDA MCP 只有：`open_database`、`execute_python`、`reference`、`list_databases`、`save_database`、`close_database`。

已有且应保留的计算机快路径（不要删）：先读 `notes\device_map.computer.summary.txt`；`.mfs` 先 `sqlite_master` 再一条带 `LIMIT` 的 `SELECT`；表名 `Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN`、`Linux_UsbInfo`、`Win_WeChat`、`Any_Chrome` / `Any_ChromiumBrowser`、`Any_OfficeMetaInfo`；原始盘 `query_device_mount_path`；嵌套 VM 走现有 `myos_nested_vm.py`；不重读约 70 KB 概览；不对约 13 GB 文档树全量 grep；浏览器密码走现有 `chrome_login_decrypt.py`；哈希对候选现算 MD5。

## 文件地图

创建：

- `hermes/bin/tests/test_hexp_routing.py`
- `hermes/bin/hexp_import_check.py`
- `hermes/skill-library/dfir-curated/20261107-hexp/profile-map.json`
- `hermes/skill-library/dfir-curated/20261107-hexp/skills/security/myos-results-analysis/`（源副本，含 stub 与 rich 两份）
- `hermes/skill-library/dfir-curated/20261107-hexp/skills/security/bill-flow-analysis/`
- `hermes/skill-library/dfir-curated/20261107-hexp/skills/security/forensic-record-draft/`
- `hermes/skill-library/dfir-curated/20261107-hexp/references/evidence-record.md`
- `hermes/skill-library/dfir-curated/20261107-hexp/references/server-artifact-checklist.md`
- `hermes/skill-library/dfir-curated/20261107-hexp/references/bill-flow-template.md`
- `docs/superpowers/plans/` 已有本文件，不要另写第二份方案覆盖 Codex 原文

修改：

- `hermes/bin/dfir_router.py`
- `hermes/bin/dfir_plan.py`
- `hermes/profiles/dfir-myos/skills/security/myos-results-analysis/SKILL.md`
- `hermes/profiles/dfir-max/skills/security/myos-results-analysis/SKILL.md`
- 四个无 MYOS profile 的同名 `SKILL.md` 换成 stub
- `hermes/profiles/dfir-myos/SOUL.md` 与 `dfir-max/SOUL.md`：只替换错误工具名
- 六个 profile 上字节相同的 `memory-forensics-local`、`ida-reverse`、`wire-toutetu`、`digital-forensics`、`android-malware-analysis`：各加一节，然后六份保持彼此相同
- `dfir-myos` 与 `dfir-max` 的 `android-app-forensics/SKILL.md`、富版 `linux-loader`、富版 `windows-loader`
- 四个薄版 `linux-loader` / `windows-loader`：只加“无 MYOS / 无 BootMagix”边界，不把富版 MYOS 快路径拷进去
- `docs/通用取证框架.md`：文末追加一节，不改第 2 节结构

不修改：`config.yaml` 的 `mcp_servers`、`model`、`hooks`、`memory`；`memories/MEMORY.md`；Codex 方案原文。

---

### Task 1: 备份与检查器骨架

**Files:**
- Create: `hermes/bin/hexp_import_check.py`
- Create: `hermes/bin/tests/test_hexp_routing.py`
- Create: `hermes/profiles/.backup-20261107-hexp-import/README.md`

**Interfaces:**
- Consumes: 无
- Produces: `hexp_import_check.forbidden_hits(text: str) -> list[str]`，命中 Global Constraints 里的可调用产品工具名时返回命中词；“未接入，不要调用”所在行不算命中。`backup_touched(dest: Path, paths: list[Path]) -> None` 只复制列出的文件，目标已存在则失败退出。

- [ ] **Step 1: 写失败测试**

在 `hermes/bin/tests/test_hexp_routing.py` 写：

```python
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BIN))
import hexp_import_check as check


class ImportCheckTest(unittest.TestCase):
    def test_forbidden_detects_ges_call_but_allows_denial(self):
        self.assertIn("ges status", check.forbidden_hits("先执行 ges status"))
        self.assertEqual(check.forbidden_hits("GE-BootMagix 未接入，不要调用 create-vm"), [])

    def test_backup_refuses_existing_dest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            src = root / "a.txt"
            src.write_text("x", encoding="utf-8")
            dest = root / "bak"
            dest.mkdir()
            with self.assertRaises(SystemExit) as caught:
                check.backup_touched(dest, [src])
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python -I hermes/bin/tests/test_hexp_routing.py`

Expected: FAIL，`hexp_import_check` 不存在。不要安装 pytest。后续任务都用这一条命令。

- [ ] **Step 3: 实现检查器并做备份**

`forbidden_hits` 扫描这些子串，但跳过包含“未接入，不要调用”的行：`ges status`、`ges case`、`ges read`、`ges ls`、`Goldeneyes://`、`thunder-app-`、`survey_binary`、`ida_pro_mcp`、`SetBreakpoint`、`LoadBinary`、`pywmxclient`、`clonezilla-to-e01`。`create-vm` 只在该行没有“不要调用”时算命中。

`backup_touched` 把相对 `hermes/` 的路径复制到 dest 下，保持相对结构。dest 已存在则 `SystemExit(2)`。

然后用它把 Task 2–9 将要改的现文件复制到 `hermes/profiles/.backup-20261107-hexp-import/`。README 只写三行：日期、来源、禁止覆盖旧备份。不要复制 `state.db`、头像、sessions。

- [ ] **Step 4: 再跑测试**

Expected: PASS。备份目录存在，且 `Test-Path` 旧的三个 `.backup-20261031*` / `.backup-20261101*` 仍在。

- [ ] **Step 5: 检查点**

把 `hexp_import_check.py` 和测试文件复制到 `checkpoints/task-1/`。

---

### Task 2: 修正解题路由

**Files:**
- Modify: `hermes/bin/dfir_plan.py`（`DEFAULT_SKILLS`、`DOMAIN_RULES`、`build_plan`）
- Modify: `hermes/bin/dfir_router.py`（`local_skill`、`main` 的 context 字符串）
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: `build_plan(q: int, question: str, notes: Path | None) -> Plan`，`local_skill(message: str) -> str | None`
- Produces: 同一签名。`local_skill` 新增返回值 `bill-flow-analysis`、`forensic-record-draft`。context 字符串必须包含首选 profile 名，以及“skill_view 失败就改口到该 profile，不要编造工具名”。

- [ ] **Step 1: 写失败测试**

```python
class RoutingTest(unittest.TestCase):
    def test_domain_skills_are_installed_names(self):
        import tempfile
        cases = {
            "这个内存镜像里有没有代码注入": ("dfir-mem", ["memory-forensics-local"]),
            "分析这个 pcap 里的 DNS 隧道": ("dfir-pcap", ["wire-toutetu"]),
            "用 IDA 看这个 exe 的导入表": ("dfir-re", ["ida-reverse", "android-malware-analysis"]),
            "电脑检材最后一次开机时间": ("dfir-myos", ["myos-results-analysis", "linux-loader", "windows-loader", "digital-forensics"]),
            "银行流水里有没有快进快出": ("dfir-pcap", ["bill-flow-analysis"]),
            "MYOS 里这台 Linux 的开机时间": ("dfir-myos", ["myos-results-analysis", "linux-loader", "windows-loader", "digital-forensics"]),
        }
        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw)
            for question, (profile, skills) in cases.items():
                plan = dfir_plan.build_plan(1, question, notes=notes)
                self.assertEqual(plan.profile, profile, question)
                self.assertEqual(plan.skills, skills, question)
                self.assertNotIn("utm-forensic-cli", plan.skills)

    def test_router_names_one_installed_skill(self):
        self.assertEqual(dfir_router.local_skill("火眼里查 USB"), "myos-results-analysis")
        self.assertEqual(dfir_router.local_skill("银行流水快进快出"), "bill-flow-analysis")
        self.assertEqual(dfir_router.local_skill("起草电子数据取证笔录"), "forensic-record-draft")
        self.assertEqual(dfir_router.local_skill("这个内存镜像有没有注入"), "memory-forensics-local")
```

后续任务的测试也写成 `unittest.TestCase` 方法，加进同一个文件。不要使用 pytest。

- [ ] **Step 2: 运行测试，确认失败**

Expected: FAIL。当前 memory/network/reverse 的 skills 含 `utm-forensic-cli`；`local_skill` 还不认识账单和笔录。

- [ ] **Step 3: 改两处路由，不改钩子注册**

`DOMAIN_RULES` 在 `computer` 之后、`network` 之前插入。不要放在 `computer` 前面，否则“电脑检材里的银行流水”会离开 `dfir-myos`：

```python
("bill", re.compile(r"银行流水|资金流水|账单|交易对手|快进快出|只进不出|资金对敲", re.I)),
```

`DEFAULT_PROFILES["bill"] = {"base": "dfir-pcap", "deep": "dfir-pcap"}`。

`DEFAULT_SKILLS` 替换为：

```python
"network": ["wire-toutetu"],
"memory": ["memory-forensics-local"],
"reverse": ["ida-reverse", "android-malware-analysis"],
"pc": ["windows-loader", "digital-forensics"],
"linux": ["linux-loader"],
"bill": ["bill-flow-analysis"],
"mac": ["digital-forensics"],
"cloud": ["digital-forensics"],
"email": ["digital-forensics"],
"database": ["digital-forensics"],
"generic": ["digital-forensics"],
```

`computer` 与 `mobile` 两行保持不动。

在 `build_plan` 里，`classify_domain` 之后：若题面含 `MYOS`、`myos`、`火眼`、`美亚` 或 `超级取证大师`，且当前 domain 属于 `linux`、`pc`、`generic`，把 domain 改成 `computer`。`memory`、`network`、`reverse`、`mobile`、`bill` 不被这条覆盖。

`local_skill` 在现有 MYOS 判断之后、手机判断之前加入账单和笔录判断。账单关键词与上面的 bill 正则一致。笔录关键词：`取证笔录`、`电子数据检查笔录`、`现场勘验笔录`、`公文 docx`。不要让单独的“报告”触发笔录技能。

`main` 的 context 在现有句子后追加一句，按返回的技能名填首选 profile：`myos-results-analysis`→`dfir-myos`，`bill-flow-analysis`→`dfir-pcap`，`memory-forensics-local`→`dfir-mem`，`wire-toutetu`→`dfir-pcap`，`ida-reverse` 与 `android-malware-analysis`→`dfir-re`，`forensic-record-draft`→`dfir`。并写：若 `skill_view` 失败或当前工具列表没有该技能要求的 MCP，停止并指出这个 profile，不要编造工具名。

- [ ] **Step 4: 再跑 Task 2 的测试**

Expected: PASS。

- [ ] **Step 5: 检查点**

复制两个 Python 文件到 `checkpoints/task-2/`。

---

### Task 3: MYOS 二次分析卡片

**Files:**
- Modify: `hermes/profiles/dfir-myos/skills/security/myos-results-analysis/SKILL.md`
- Modify: `hermes/profiles/dfir-max/skills/security/myos-results-analysis/SKILL.md`（与上一份改完后必须字节相同）
- Modify: `dfir`、`dfir-mem`、`dfir-pcap`、`dfir-re` 的同名 `SKILL.md` 为 stub
- Create: `hermes/profiles/dfir-myos/skills/security/myos-results-analysis/references/myos-secondary-card.md`
- 同样复制到 `dfir-max` 的同名 references 目录
- Create: 源副本到 `hermes/skill-library/dfir-curated/20261107-hexp/skills/security/myos-results-analysis/`
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: Task 1 的 `forbidden_hits`；上文 MYOS 白名单
- Produces: 富技能在 frontmatter 之后、任何旧的 `## Computer forensics` 之前有 `## 二次分析第一跳`。stub 小于 800 字节，不含 `sqlite_query`。

- [ ] **Step 1: 写失败测试**

测试读取六个 SKILL.md：

- `dfir-myos` 与 `dfir-max` 的 SHA-256 相同，且与 `dfir` 的不同。
- 富技能中 `## 二次分析第一跳` 的位置早于 `## Computer forensics methodology`。
- 富技能仍含这些原句或原表名：`device_map.computer.summary.txt`、`sqlite_master`、`LIMIT`、`Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN`、`query_device_mount_path`、`chrome_login_decrypt.py`、`tool_search`。
- 富技能不含 `query_phone_file_forensics_result_summary`。
- 从富技能提取的 `query_[a-z0-9_]+` 与 `sqlite_query` 都是白名单短名的子集。
- `forbidden_hits(富技能全文)` 为空。
- 四个 stub 每个都小于 800 字节，含 `dfir-myos` 和 `不要调用`，不含 `sqlite_query`。

- [ ] **Step 2: 运行测试，确认失败**

Expected: FAIL。四个旧副本仍是 3668 字节完整技能，富技能还没有“二次分析第一跳”。

- [ ] **Step 3: 只在富技能顶部加卡片，四个无 MCP 的副本换成 stub**

卡片用中文，控制在 180 行以内，放进 SKILL.md 顶部，细节放 `references/myos-secondary-card.md`。卡片必须写清：

1. 先读已有 `notes\device_map.computer.summary.txt` 或手机的 `notes\device_map.myos.summary.txt`。没有索引才调用概览工具，概览落盘后不要整份读回上下文。
2. 电脑题和手机题分开。电脑第一跳是插件库 `.mfs`；手机第一跳是 `appMfsPath` / `apklist.mfs` / `MApps.mfs`。不要把 Linux 开关机表用到手机题。
3. 一次只补一个缺口：先 `sqlite_master`，再一条带 `LIMIT` 的 `SELECT`。禁止 `PRAGMA table_info`。`not authorized` 先核对 caseId 和 mount，不要原样重试。
4. 搜索命中、文件名、插件标签只是线索。没有当次 `sqlite_query` 或 `query_current_node_data` 回执的句子，写成“未取到”，不要写成不存在。
5. `quick_search_content` 是有界文件搜索。`global_search_content` 会建异步任务，只提交一次，然后 `query_task_status`。不要用它开局。
6. `create_file_index_task`、`decrypt_partition`、`restart_computer_forensics` 会改状态。二次分析请求本身不是授权。
7. 嵌套 VM 仍走现有 `myos_nested_vm.py`，先 `--dry-run`。不要和宿主时间线混写。
8. 角标写成 `caseId + materialId + dbPath + 表名 + 查询 + 行`。不要写 `Goldeneyes://`，不要调用 `ges`。
9. 同一分支两次零命中就换表或写 pending。解题只提交答案，不写笔录，不写 writeup。
10. 工具短名表只列白名单。写明调用前看 `tool_search`，保留哈希后缀。
11. 题面是独立流水/账单文件、没有 MYOS 插件库时，不要 `sqlite_query`。交接 `dfir-pcap` 的 `bill-flow-analysis`。

GoldenEyes 包里值得留下的只有：不默认第一条案件、命中不是证据、部分结果不是完整结果、事实/推断/待核验分开、原始检材只读。把这五条写进卡片，不要写 `ges` 命令。

stub 全文固定为：本 profile 没有 `myos-forensics` MCP。不要调用任何 MYOS 工具。告诉用户改用 `dfir-myos`。不要根据记忆补查询结果。

富技能其余正文，包括 `Computer forensics fast path` 和 references 链接，保持不动。

- [ ] **Step 4: 再跑测试**

Expected: PASS。`forbidden_hits` 为空。两个富技能哈希相同。

- [ ] **Step 5: 检查点**

复制六个 SKILL.md 和新建的 reference 到 `checkpoints/task-3/`。源副本与 profile 副本哈希一致。

---

### Task 4: 证据收口，并修正 SOUL 里的幽灵工具名

**Files:**
- Create: `hermes/skill-library/dfir-curated/20261107-hexp/references/evidence-record.md`
- Copy 到六个 profile 的 `skills/security/digital-forensics/references/evidence-record.md`
- Modify: 六个 `digital-forensics/SKILL.md`，在 When to Use 后加不超过 15 行的“结论收口”
- Modify: `dfir-myos` 与 `dfir-max` 的 `skills/forensics/android-app-forensics/SKILL.md`，加同样的 15 行指针
- Modify: `hermes/profiles/dfir-myos/SOUL.md`
- Modify: `hermes/profiles/dfir-max/SOUL.md`
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: hexp 的证据等级原名，不新造同义词
- Produces: `evidence-record.md` 含八个字段名 `source`、`object`、`time`、`action`、`receipt`、`grade`、`gap`、`handoff`，以及等级 `E1` `E2` `E3` `E4` 和五档结论强度原词

- [ ] **Step 1: 写失败测试**

- 六个 `digital-forensics/SKILL.md` 改完后哈希相同。
- 每个都含 `references/evidence-record.md`。
- evidence-record 含八个字段名、`E1` 到 `E4`、`已确认`、`待验证`。
- evidence-record 含这句话：解题提交值不得包含 E1、E2、E3、E4 或结论强度原词；没有 receipt 的句子写“未取到”。
- 两个 SOUL 不含 `query_phone_file_forensics_result_summary`，仍含 `query_phone_forensics_results_overview`。
- 两个 SOUL 的字节数相对备份增加不超过 200。

- [ ] **Step 2: 运行测试，确认失败**

Expected: FAIL。SOUL 仍含幽灵工具名；reference 不存在。

- [ ] **Step 3: 写短参考，并只替换 SOUL 中的工具名**

`evidence-record.md` 用一张表定义八字段。`grade` 沿用 hexp：`E1` 静态声明或清单，`E2` 可定位源码或反编译，`E3` 本次运行回执，`E4` 至少一条 E2 加一条 E3 的交叉，不能由单个插件直接生成。结论强度用“已确认 / 高度支持 / 初步支持 / 线索提示 / 待验证”。写明：请求存在不等于数据上传；未观察到不等于不存在；空结果、截断、任务未完成必须披露。

本机映射写在同一文件，不要写进 SOUL：

- APK 的 E1/E2 只来自已有 jadx / `android-malware-analysis` 回执。没有抓包或动态回执时，E3 写“未取到”，不要调用 `thunder-app-*`。
- 内存的 E3 只来自 memforensics / lovelymem 插件回执。
- 流量的 E3 只来自 wiremcp 或 `wire-toutetu` 的 `EVT-*`。
- MYOS 的 E3 只来自白名单工具的当次回执。

SOUL 替换：`query_phone_file_forensics_result_summary` 改为已在白名单中的 `query_phone_forensics_results_overview`。手机链变成 `query_open_cases` → `query_materials` → `query_phone_forensics_results_overview`。不要加新段落。

`digital-forensics` 与 `android-app-forensics` 的新增节只说：下结论前读 `references/evidence-record.md`；解题答案不写等级词。不要把模板正文贴进 SKILL.md。

- [ ] **Step 4: 再跑测试**

Expected: PASS。

- [ ] **Step 5: 检查点**

复制 SOUL、evidence-record 和改过的 SKILL.md 到 `checkpoints/task-4/`。

---

### Task 5: 把内存、IDA、流量包收成现有技能的边界节

**Files:**
- Modify: 六个 profile 的 `skills/security/memory-forensics-local/SKILL.md`
- Modify: 六个 profile 的 `skills/security/ida-reverse/SKILL.md`
- Modify: 六个 profile 的 `skills/security/android-malware-analysis/SKILL.md`
- Modify: 六个 profile 的 `skills/security/wire-toutetu/SKILL.md`
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: 这些文件目前跨六个 profile 哈希相同。改完后每组仍必须相同。
- Produces: 每个技能多一节，不超过 40 行。不新建 `re-x64dbg-dynamic-debug`。

- [ ] **Step 1: 写失败测试**

对每组六个文件：哈希相同；`forbidden_hits` 为空；

- `memory-forensics-local` 含“YARA 只在用户给出规则时扫描”和“凭据提取不是初筛步骤”，且仍含 `memory_extract_credentials` 的现有限制。
- `ida-reverse` 含六工具名 `list_databases`、`open_database`、`execute_python`、`reference`、`save_database`、`close_database`，并含“x64dbg 未接入，不要调用”。
- `android-malware-analysis` 含“没有运行回执就写未取到”和“不要调用 thunder-app”。
- `wire-toutetu` 含“本技能不分析银行流水”和 `bill-flow-analysis`。

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 各加一节，六份一起改**

内存节：按问题选一个已有 MCP 短名，不默认全量 triage。进程、注入、网络、命令历史、隐藏驱动必须分开写“未检查 / 检查失败 / 本次未发现”。单项插件结果不能写成恶意结论。LSASS 或凭据只有用户点名时才进入，秘密不进聊天。这是从 memory-forensics `EXPERT.md` 抽出的全部可执行内容；不要另建同名新技能。

IDA 节：静态分析只用现有六工具，批量查询放进一次 `execute_python`。原样本只读；`save_database` 仅在用户要求保存注释时调用。动态调试 MCP 未接入，动态行为写“未取到”。不要写补丁、断点绕过或 dump 后执行。

APK 节：本环境没有 AppAnalyzer。静态和源码走 jadx 与本技能已有流程。没有本次设备运行、抓包或 Frida 回执时，不回答“实际发生了”。不要调用不存在的 thunder 技能，也不要为了凑 E4 去发起新的动态任务。

流量节：本技能只分析已有 pcap/pcapng，不启动抓包。银行流水、账单、快进快出改 `skill_view("bill-flow-analysis")`。单边命中写“待交叉”，不要把流量会话直接写成资金事实。

- [ ] **Step 4: 再跑测试**

Expected: PASS。六份哈希仍各组一致。

- [ ] **Step 5: 检查点**

复制这四个技能到 `checkpoints/task-5/`。源副本放进 `20261107-hexp`。

---

### Task 6: 服务器包只留下工件清单和未接入边界

**Files:**
- Create: `hermes/skill-library/dfir-curated/20261107-hexp/references/server-artifact-checklist.md`
- Copy 到六个 profile 的 `skills/forensics/linux-loader/references/` 和 `windows-loader/references/`
- Modify: 富版 loader（仅 `dfir-myos`、`dfir-max`）与薄版 loader（其余四个），各自加不超过 12 行

**Interfaces:**
- Consumes: 富版与薄版哈希现在就不同，必须继续不同
- Produces: 清单文件；富版仍含 `myos-results-analysis` 快路径；薄版不含 `query_computer_forensics_results_overview`

- [ ] **Step 1: 写失败测试**

- 清单含 Windows 侧 `Security`、`System`、`PowerShell`、`RDP`、IIS、计划任务，以及 Linux 侧 `auth`、`journal`、`sshd_config`、`sudoers`、`cron`、`systemd`。
- 清单含“未接入，不要调用 create-vm”和“未接入，不要调用 clonezilla-to-e01”。
- `forbidden_hits(清单)` 为空。
- 富版 `linux-loader` 仍含 `myos-results-analysis`；薄版不含 `query_computer_forensics_results_overview`。
- 薄版含“本 profile 没有 MYOS MCP，计算机结果题改用 dfir-myos”。

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 写清单，不要把仿真步骤写成操作**

清单是检查表，不是命令序列。每行是“看什么工件、哪类结论需要第二来源”。写明：没有 BootMagix，不能启动虚拟机，不能把“如果仿真会看到”写成检材事实。富版 loader 的新增节只加一句“服务器题先走 MYOS 插件库，原始日志是第二来源，清单在 references”。薄版只加交接句和清单指针。不要把富版文件拷到薄版 profile。

不新增 `server-forensics-report` 技能。`attack-analysis` 已经覆盖 Web 日志时间线，不要改它。

- [ ] **Step 4: 再跑测试**

Expected: PASS。

- [ ] **Step 5: 检查点**

复制清单和两个版本的 loader SKILL.md 到 `checkpoints/task-6/`。

---

### Task 7: 账单技能，只做本地只读分析

**Files:**
- Create: `hermes/profiles/dfir-pcap/skills/security/bill-flow-analysis/SKILL.md`
- Create: `hermes/profiles/dfir-pcap/skills/security/bill-flow-analysis/references/bill-flow-template.md`
- Copy 这两个文件到 `dfir-max` 的同名目录
- Create: 源副本 `hermes/skill-library/dfir-curated/20261107-hexp/skills/security/bill-flow-analysis/`
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: Task 2 已会路由到这个技能名
- Produces: description 恰好以 `Use when` 开头，且不超过 120 字符。SKILL.md 正文不超过 4000 字节。模板可以到 22 KB，但只能在 references。

- [ ] **Step 1: 写失败测试**

- `dfir`、`dfir-mem`、`dfir-re`、`dfir-myos` 没有这个技能目录。
- `dfir-pcap` 与 `dfir-max` 的 SKILL.md 哈希相同。
- description 含“没有 WebMatrix”或“不要调用 WMX”。
- 正文含统计口径：交易总金额 = 转入 + 转出；交易净额 = 转入 - 转出；未指定时区时声明 `+8`。
- 正文含“战法命中不是违法认定”和“未命中不是确认无异常”。
- 正文含“单题不要读 references/bill-flow-template.md”。
- `forbidden_hits` 为空，且正文不含 `pywmxclient`。
- 模板文件存在，且 SKILL.md 没有把模板表格正文内联进去（用“模板行数”断言：SKILL.md 不含“快进快出时间窗口”这一模板字段名；该字段只在 reference）。

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 写技能，模板从 hexp 复制到 references**

description 用这一句，不要加长：

`Use when 银行流水或账单需本地只读分析；本环境没有 WebMatrix，不要调用 WMX。`

正文流程：

1. 只读用户给出的文件。不把源文件复制进工作区，不改源文件。
2. 用 `python -I` 读 CSV/TXT/XLSX。PDF 若没有现成本地解析器，写“未取到”，不要安装软件。
3. 先报编码、表头、行数、时间范围、借贷方向字段。字段对不上就停，不猜列。
4. 回答用户的那一个问题。只有用户要求完整报告时才读模板。
5. 证据定位是文件路径、工作表、行号。不要编 WMX 虚拟路径 `/case/datasource`。
6. 和流量交叉时，两边都要有回执。一边有记录只写“待交叉”。
7. 内部转账、冲正、退款是否去重必须写明。

模板从 `_hexp_review_20261106` 里的 `资金流水分析报告模板.md` 原样复制为 `bill-flow-template.md`，删掉 hexp 说明里的 WMX CLI 步骤；保留章节和占位符。若复制后仍含 `pywmxclient` 或 `ges `，删掉那些句子再入库。

- [ ] **Step 4: 再跑测试**

Expected: PASS。

- [ ] **Step 5: 检查点**

复制技能目录到 `checkpoints/task-7/`。

---

### Task 8: 笔录技能，默认不进入解题

**Files:**
- Create: `hermes/profiles/dfir/skills/security/forensic-record-draft/SKILL.md`
- Create: `hermes/profiles/dfir/skills/security/forensic-record-draft/references/four-record-types.md`
- Create: `hermes/profiles/dfir/skills/security/forensic-record-draft/scripts/md_to_gongwen_docx.py`
- Copy 到 `dfir-myos` 与 `dfir-max`。不要复制到 mem/pcap/re。
- Test: `hermes/bin/tests/test_hexp_routing.py`

**Interfaces:**
- Consumes: hexp 笔录包的四类模式、防编造、哈希、敏感信息规则；脚本只复制不执行
- Produces: 技能名 `forensic-record-draft`。description 不超过 120 字符，且含“仅当用户明确要求笔录”。

- [ ] **Step 1: 写失败测试**

- 只有 `dfir`、`dfir-myos`、`dfir-max` 有该目录，三份 SKILL.md 哈希相同。
- 技能全文不含“成功接收到公网”。
- 含 `〔待确认：字段〕`、四种模式名“现场勘验”“远程勘验”“电子数据提取”“电子数据检查”。
- 含“不得把征求意见稿写成已生效依据”。
- 含“解题提交不要调用本技能”。
- 脚本文件存在，且测试不 import 它、不运行它。
- `forbidden_hits` 为空。

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 写技能并复制脚本**

description：

`Use when 用户明确要求电子数据取证笔录或公文 docx；不要用于解题提交。`

正文：

- 没有单位模板就声明这是通用草稿，不冒充制式文书。
- 缺字段写 `〔待确认：字段〕`，不用示例值。
- 哈希逐字抄录，不补位，不改大小写后宣称为原值。原文、镜像、导出目录、封存载体的校验值分开写。
- 密码、令牌、密钥不进正文。
- 模型不能确认在场、签名、封存、移交。
- 四种模式只决定要素，不自动决定正式文书名。
- 《公安机关办理刑事案件电子数据取证规则》2019-02-01 起施行这句话只能作为待核实依据，不能当作已经核过的现行法。征求意见稿不是生效依据。
- 用户要求 docx 时，用技能目录里的 `scripts/md_to_gongwen_docx.py`。先 `python -I -c "import docx"`。失败就交付 Markdown，并写“docx 未生成”，不要安装依赖，不要宣称已经生成。
- 脚本从 hexp 解包目录原样复制。不要改脚本逻辑。

`four-record-types.md` 只保留四类模式的要素清单，从 hexp 的 `四类取证笔录要素与模板.md` 压缩，去掉示例单位、人名、哈希。

- [ ] **Step 4: 再跑测试**

Expected: PASS。确认测试进程没有生成 `.docx`。

- [ ] **Step 5: 检查点**

复制三个 profile 的技能目录到 `checkpoints/task-8/`。

---

### Task 9: 文档只追加入口

**Files:**
- Modify: `docs/通用取证框架.md`
- Create: `reports/DFIR-hexp修订说明-2026-11-07.md`

**Interfaces:**
- Consumes: Task 2 的最终路由
- Produces: 框架文末一节；修订说明指向本计划，不覆盖 Codex 原文

- [ ] **Step 1: 写失败测试**

```python
class DocsTest(unittest.TestCase):
    def test_docs_point_at_plan_without_replacing_codex(self):
        framework = Path("docs/通用取证框架.md").read_text(encoding="utf-8")
        self.assertIn("## 11. hexp 导入后的入口", framework)
        self.assertIn("utm-forensic-cli", framework)
        note = Path("reports/DFIR-hexp修订说明-2026-11-07.md").read_text(encoding="utf-8")
        self.assertIn("docs/superpowers/plans/2026-11-07-hexp-dfir-capability.md", note)
        codex = Path("reports/DFIR-hexp能力沉淀实施方案-2026-11-07.md").read_text(encoding="utf-8")
        self.assertTrue(codex.startswith("# DFIR hexp 能力沉淀实施方案"))
```

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 追加，不重写**

在 `docs/通用取证框架.md` 文末加 `## 11. hexp 导入后的入口`。不要改第 1–10 节，包括第 4 节和第 10 节里仍写着 `utm-forensic-cli` 的旧句。新节用一张表列出 Task 2 的 profile 和技能，并写明：第 4 节和第 10 节的技能列已被本计划取代；计算机已有 MYOS 结果的题走 `dfir-myos`，第一跳是 `myos-results-analysis`；内存题和流量题不再使用 `utm-forensic-cli`。`dfir-mem` / `dfir-pcap` 上对应技能本来就已安装，缺的是路由，不是新技能目录。

修订说明用十行以内：Codex 方案保留为对照；本计划是实施依据；列出五条修正（注册方式、memory 不注入、ges 不可调用、路由指向禁用技能、不新建十一份常驻技能）。不要复制本计划全文。

- [ ] **Step 4: 再跑测试**

Expected: PASS。

- [ ] **Step 5: 检查点**

复制这两个文档到 `checkpoints/task-9/`。

---

### Task 10: 全量门禁

**Files:**
- Modify: `hermes/bin/hexp_import_check.py`
- Modify: `hermes/bin/tests/test_hexp_routing.py`
- Create: `hermes/skill-library/dfir-curated/20261107-hexp/profile-map.json`

**Interfaces:**
- Consumes: Task 3–8 的 profile 副本
- Produces: `hexp_import_check.main() -> int`。0 表示 profile-map 中每个源文件与列出的 profile 副本哈希相同，且扫描范围内 `forbidden_hits` 为空。

- [ ] **Step 1: 写 profile-map.json**

键是源相对路径，值是 profile 名列表。至少包括：

- 富 `myos-results-analysis/SKILL.md` → `dfir-myos`、`dfir-max`
- stub → `dfir`、`dfir-mem`、`dfir-pcap`、`dfir-re`
- `bill-flow-analysis/SKILL.md` → `dfir-pcap`、`dfir-max`
- `forensic-record-draft/SKILL.md` → `dfir`、`dfir-myos`、`dfir-max`
- `evidence-record.md` → 六个 profile 的 `digital-forensics/references/`
- `server-artifact-checklist.md` → 六个 profile 的两个 loader references

不要把富 myos 技能列进四个无 MYOS 的 profile。

- [ ] **Step 2: 写失败测试，然后实现 `main`**

测试调用 `main()`，期望 0。实现只做哈希比对和禁词扫描，不修复、不删除。输出只含 profile、相对路径、issue，不含文件正文。

另外扫描改过的 SOUL，确认不含 `query_phone_file_forensics_result_summary`。

- [ ] **Step 3: 运行全部测试**

Run: `python -I hermes/bin/tests/test_hexp_routing.py`

Expected: PASS。然后 `python -I hermes/bin/hexp_import_check.py`，期望退出码 0。

- [ ] **Step 4: 人工核对，不跑案件**

打开 `dfir-myos` 的 `config.yaml`，确认 `mcp_servers.myos-forensics.tools.include` 与备份字节相同。确认 `memory_enabled` 仍是 `false`。确认 `8095` 仍在。确认没有新的 `.docx`。

- [ ] **Step 5: 检查点**

复制 `profile-map.json` 和检查器到 `checkpoints/task-10/`。

## 明确不做

- 不打开 `memory_enabled`。现有 `MEMORY.md` 继续留在磁盘上，供人读，不进模型。若以后要打开，先删掉与 SOUL 重复的计算机段落，再单独测量 prefill，那是另一次改动。
- 不把八包技能挂进 `dfir-max` 的 SOUL。
- 不修改 `dfir_skill_drift.py` 去要求六份副本相同。富/薄分裂是有意的。
- 不跑 DIDCTF，不跑 2025 FIC，不调用 MYOS。那些是导入后的人工回归，不是本计划的完成条件。
- 不把 `phase-gated-docx-learning` 从 disabled 里放出来。它有 60 KB，和笔录技能不是一回事。

## 导入后的人工回归（本计划不执行）

用已有题，不找新题。每类一题即可：

- 计算机题：第一跳应是 summary 或已有 device_map，不应重读 70 KB 概览，不应出现 `ges`。
- 手机题：不应调用 `query_phone_file_forensics_result_summary`。
- 内存题：`dfir_plan` 选出的 profile 是 `dfir-mem`，技能是 `memory-forensics-local`。
- 流量题：技能是 `wire-toutetu`，不是 `utm-forensic-cli`。
- 流水题：不读 22 KB 模板，不调用 WMX。
- 笔录请求：草稿含待确认标记，不含“成功接收到公网”。解题请求不应进入该技能。

正确率只计算有回执的答案。“未取到”不算错；把“未取到”写成已证实算错。

## Self-review

- Spec coverage：Codex 的八包都有归宿。APK、EXE、GoldenEyes、memory、traffic 并入已有技能；服务器只留清单；账单和笔录是仅有的新技能；嵌套 zip 和头像排除。MYOS 二次分析是 Task 3 和 Task 4。路由修复是 Task 2，补上 Codex 未写的速度缺陷。
- memory 不注入这一事实已写成硬约束，避免实施者按 Codex 第 6 节去新建 2–4 KB memory 却没有任何运行时效果。
- 富/薄技能分离有测试钉住，避免“复制到全部 profile”毁掉 `dfir-myos` 的计算机快路径。
- 未改 MCP 白名单。幽灵工具名只在 SOUL 文本中替换，不把新工具加进 config。
