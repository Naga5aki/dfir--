import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BIN))
import dfir_plan
import dfir_router
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


class RoutingTest(unittest.TestCase):
    def test_domain_skills_are_installed_names(self):
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


class MyosSkillTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")
    allow = {
        "health_check_dbus", "query_cases", "query_open_cases", "open_case", "query_materials",
        "load_case", "add_image_material", "add_disk_material", "add_file_collection_material",
        "query_computer_forensics_results_overview", "query_device_info", "query_device_mount_path",
        "query_current_node_data", "quick_search_files", "sqlite_query", "create_file_index_task",
        "quick_search_content", "global_search_content", "query_task_status", "wait_task_completion",
        "query_phone_forensics_results_overview", "query_encrypt_types", "decrypt_partition",
        "query_decrypt_task_status", "restart_computer_forensics",
    }

    def test_rich_card_and_thin_stubs(self):
        rich = {}
        for name in ("dfir-myos", "dfir-max"):
            rich[name] = (self.root / name / "skills/security/myos-results-analysis/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(rich["dfir-myos"].encode()).hexdigest(),
            hashlib.sha256(rich["dfir-max"].encode()).hexdigest(),
        )
        stub_now = (self.root / "dfir/skills/security/myos-results-analysis/SKILL.md").read_text(encoding="utf-8")
        self.assertNotEqual(
            hashlib.sha256(stub_now.encode()).hexdigest(),
            hashlib.sha256(rich["dfir-myos"].encode()).hexdigest(),
        )
        body = rich["dfir-myos"]
        self.assertLess(body.index("## 二次分析第一跳"), body.index("## Computer forensics methodology"))
        for needle in (
            "device_map.computer.summary.txt",
            "sqlite_master",
            "LIMIT",
            "Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN",
            "query_device_mount_path",
            "chrome_login_decrypt.py",
            "tool_search",
        ):
            self.assertIn(needle, body)
        self.assertNotIn("query_phone_file_forensics_result_summary", body)
        names = set(re.findall(r"query_[a-z0-9_]+", body))
        if "sqlite_query" in body:
            names.add("sqlite_query")
        self.assertTrue(names <= self.allow, names - self.allow)
        self.assertEqual(check.forbidden_hits(body), [])
        for name in ("dfir", "dfir-mem", "dfir-pcap", "dfir-re"):
            raw = (self.root / name / "skills/security/myos-results-analysis/SKILL.md").read_bytes()
            self.assertLess(len(raw), 800, name)
            text = raw.decode("utf-8")
            self.assertIn("dfir-myos", text)
            self.assertIn("不要调用", text)
            self.assertNotIn("sqlite_query", text)


class EvidenceCloseTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")
    backup = root / ".backup-20261107-hexp-import" / "profiles"

    def test_evidence_record_and_soul_tool_name(self):
        texts = []
        for name in ("dfir", "dfir-max", "dfir-mem", "dfir-myos", "dfir-pcap", "dfir-re"):
            skill = self.root / name / "skills/security/digital-forensics/SKILL.md"
            texts.append(skill.read_text(encoding="utf-8"))
            ref = skill.parent / "references/evidence-record.md"
            self.assertTrue(ref.exists(), name)
            self.assertIn("references/evidence-record.md", texts[-1])
        self.assertEqual(len({hashlib.sha256(t.encode()).hexdigest() for t in texts}), 1)
        record = (self.root / "dfir/skills/security/digital-forensics/references/evidence-record.md").read_text(encoding="utf-8")
        for needle in ("source", "object", "time", "action", "receipt", "grade", "gap", "handoff", "E1", "E2", "E3", "E4", "已确认", "待验证"):
            self.assertIn(needle, record)
        self.assertIn("解题提交值不得包含 E1、E2、E3、E4 或结论强度原词；没有 receipt 的句子写“未取到”。", record)
        for name in ("dfir-myos", "dfir-max"):
            soul = (self.root / name / "SOUL.md").read_bytes()
            old = (self.backup / name / "SOUL.md").read_bytes()
            text = soul.decode("utf-8")
            self.assertNotIn("query_phone_file_forensics_result_summary", text)
            self.assertIn("query_phone_forensics_results_overview", text)
            self.assertLessEqual(len(soul) - len(old), 200, name)


class DomainBoundaryTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")
    profiles = ("dfir", "dfir-max", "dfir-mem", "dfir-myos", "dfir-pcap", "dfir-re")

    def _texts(self, rel: str) -> list[str]:
        texts = [(self.root / name / rel).read_text(encoding="utf-8") for name in self.profiles]
        self.assertEqual(len({hashlib.sha256(t.encode()).hexdigest() for t in texts}), 1, rel)
        for text in texts:
            self.assertEqual(check.forbidden_hits(text), [], rel)
        return texts

    def test_memory_ida_apk_traffic_boundaries(self):
        memory = self._texts("skills/security/memory-forensics-local/SKILL.md")[0]
        self.assertIn("YARA 只在用户给出规则时扫描", memory)
        self.assertIn("凭据提取不是初筛步骤", memory)
        self.assertIn("memory_extract_credentials", memory)
        ida = self._texts("skills/security/ida-reverse/SKILL.md")[0]
        for name in ("list_databases", "open_database", "execute_python", "reference", "save_database", "close_database"):
            self.assertIn(name, ida)
        self.assertIn("x64dbg 未接入，不要调用", ida)
        self.assertIn("仅在用户要求保存注释时调用", ida)
        self.assertNotIn("If you modified names/comments/types", ida)
        apk = self._texts("skills/security/android-malware-analysis/SKILL.md")[0]
        self.assertIn("没有运行回执就写未取到", apk)
        self.assertIn("不要调用 thunder-app", apk)
        traffic = self._texts("skills/security/wire-toutetu/SKILL.md")[0]
        self.assertIn("本技能不分析银行流水", traffic)
        self.assertIn("bill-flow-analysis", traffic)


class FrameworkDocTest(unittest.TestCase):
    path = Path(r"D:\ForensicsAgent\docs\通用取证框架.md")

    def test_routing_table_matches_runner(self):
        text = self.path.read_text(encoding="utf-8")
        section4 = text.split("## 4. 路由规则", 1)[1].split("## 5.", 1)[0]
        self.assertNotIn("utm-forensic-cli", section4)
        self.assertIn("memory-forensics-local", section4)
        self.assertIn("wire-toutetu", section4)
        section10 = text.split("## 10. 当前限制", 1)[1].split("## 11.", 1)[0]
        self.assertNotIn("utm-forensic-cli", section10)
        section11 = text.split("## 11. hexp 导入后的入口", 1)[1]
        self.assertIn("android-app-forensics", section11)
        self.assertIn("mobile-ctf-pipeline", section11)
        self.assertNotIn("已有 MYOS 结果的电脑/手机题", section11)
        self.assertIn("已有 MYOS 结果的电脑题", section11)
        self.assertIn("已有 MYOS 结果的手机题", section11)


class ServerChecklistTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")

    def test_server_checklist_does_not_flatten_loaders(self):
        checklist = (self.root / "dfir/skills/forensics/linux-loader/references/server-artifact-checklist.md").read_text(encoding="utf-8")
        for needle in ("Security", "System", "PowerShell", "RDP", "IIS", "auth", "journal", "sshd_config", "sudoers", "cron", "systemd"):
            self.assertIn(needle, checklist)
        self.assertIn("未接入，不要调用 create-vm", checklist)
        self.assertIn("未接入，不要调用 clonezilla-to-e01", checklist)
        self.assertEqual(check.forbidden_hits(checklist), [])
        rich = (self.root / "dfir-myos/skills/forensics/linux-loader/SKILL.md").read_text(encoding="utf-8")
        thin = (self.root / "dfir/skills/forensics/linux-loader/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("myos-results-analysis", rich)
        self.assertNotIn("query_computer_forensics_results_overview", thin)
        self.assertIn("本 profile 没有 MYOS MCP，计算机结果题改用 dfir-myos", thin)
        for name in ("dfir", "dfir-max", "dfir-mem", "dfir-myos", "dfir-pcap", "dfir-re"):
            for loader in ("linux-loader", "windows-loader"):
                path = self.root / name / "skills/forensics" / loader / "references/server-artifact-checklist.md"
                self.assertTrue(path.exists(), path)


class BillSkillTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")

    def test_bill_skill_is_local_and_not_broadcast(self):
        for name in ("dfir", "dfir-mem", "dfir-re", "dfir-myos"):
            self.assertFalse((self.root / name / "skills/security/bill-flow-analysis").exists(), name)
        pcap = (self.root / "dfir-pcap/skills/security/bill-flow-analysis/SKILL.md").read_text(encoding="utf-8")
        mx = (self.root / "dfir-max/skills/security/bill-flow-analysis/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(pcap.encode()).hexdigest(), hashlib.sha256(mx.encode()).hexdigest())
        desc = pcap.split("---", 2)[1]
        self.assertIn("没有 WebMatrix", desc)
        self.assertLessEqual(len(desc.split("description:", 1)[1].strip()), 120)
        self.assertTrue(desc.split("description:", 1)[1].strip().startswith("Use when"))
        self.assertLessEqual(len(pcap.encode("utf-8")), 4000)
        for needle in (
            "交易总金额 = 转入 + 转出",
            "交易净额 = 转入 - 转出",
            "+8",
            "战法命中不是违法认定",
            "未命中不是确认无异常",
            "单题不要读 references/bill-flow-template.md",
        ):
            self.assertIn(needle, pcap)
        self.assertNotIn("快进快出时间窗口", pcap)
        self.assertNotIn("pywmxclient", pcap)
        self.assertEqual(check.forbidden_hits(pcap), [])
        template = (self.root / "dfir-pcap/skills/security/bill-flow-analysis/references/bill-flow-template.md").read_text(encoding="utf-8")
        self.assertIn("快进快出时间窗口", template)
        self.assertNotIn("pywmxclient", template)


class RecordSkillTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")

    def test_record_skill_is_draft_only(self):
        for name in ("dfir-mem", "dfir-pcap", "dfir-re"):
            self.assertFalse((self.root / name / "skills/security/forensic-record-draft").exists(), name)
        texts = []
        for name in ("dfir", "dfir-myos", "dfir-max"):
            skill = self.root / name / "skills/security/forensic-record-draft/SKILL.md"
            texts.append(skill.read_text(encoding="utf-8"))
            self.assertTrue((skill.parent / "scripts/md_to_gongwen_docx.py").exists(), name)
        self.assertEqual(len({hashlib.sha256(t.encode()).hexdigest() for t in texts}), 1)
        body = texts[0]
        self.assertNotIn("成功接收到公网", body)
        self.assertIn("〔待确认：字段〕", body)
        for mode in ("现场勘验", "远程勘验", "电子数据提取", "电子数据检查"):
            self.assertIn(mode, body)
        self.assertIn("不得把征求意见稿写成已生效依据", body)
        self.assertIn("解题提交不要调用本技能", body)
        self.assertEqual(check.forbidden_hits(body), [])


class DocsTest(unittest.TestCase):
    def test_docs_point_at_plan_without_replacing_codex(self):
        framework = Path("docs/通用取证框架.md").read_text(encoding="utf-8")
        self.assertIn("## 11. hexp 导入后的入口", framework)
        self.assertNotIn("utm-forensic-cli", framework)
        self.assertIn("已有 MYOS 结果的手机题", framework)
        note = Path("reports/DFIR-hexp修订说明-2026-11-07.md").read_text(encoding="utf-8")
        self.assertIn("docs/superpowers/plans/2026-11-07-hexp-dfir-capability.md", note)
        codex = Path("reports/DFIR-hexp能力沉淀实施方案-2026-11-07.md").read_text(encoding="utf-8")
        self.assertTrue(codex.startswith("# DFIR hexp 能力沉淀实施方案"))


class ProfileMapTest(unittest.TestCase):
    def test_profile_map_gate(self):
        issues = check.check_profile_map()
        self.assertEqual(issues, [])
        self.assertEqual(check.main(), 0)


class ReviewFixTest(unittest.TestCase):
    root = Path(r"D:\ForensicsAgent\hermes\profiles")

    def test_phone_bill_stays_on_myos(self):
        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw)
            for question in ("检材二的微信账单", "微信交易对手账号"):
                plan = dfir_plan.build_plan(1, question, notes=notes)
                self.assertEqual(plan.profile, "dfir-myos", question)
                self.assertIn("android-app-forensics", plan.skills, question)
                self.assertNotIn("bill-flow-analysis", plan.skills, question)
        self.assertEqual(dfir_router.local_skill("检材二的微信账单"), "mobile-ctf-pipeline")
        self.assertEqual(dfir_router.local_skill("电脑检材里的银行流水"), "myos-results-analysis")
        self.assertEqual(dfir_router.local_skill("银行流水快进快出"), "bill-flow-analysis")

    def test_phone_skill_has_no_ghost_tool(self):
        for name in ("dfir-myos", "dfir-max"):
            text = (self.root / name / "skills/forensics/android-app-forensics/SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("query_phone_file_forensics_result_summary", text)

    def test_fast_path_reads_summary_before_overview(self):
        text = (self.root / "dfir-myos/skills/security/myos-results-analysis/SKILL.md").read_text(encoding="utf-8")
        section = text.split("## Computer forensics fast path", 1)[1]
        self.assertIn("device_map.computer.summary.txt", section)
        self.assertNotIn("先用 `query_computer_forensics_results_overview", section)
        for loader in ("linux-loader", "windows-loader"):
            body = (self.root / "dfir-myos/skills/forensics" / loader / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("device_map.computer.summary.txt", body)

    def test_bill_template_is_not_a_wmx_procedure(self):
        text = (self.root / "dfir-pcap/skills/security/bill-flow-analysis/references/bill-flow-template.md").read_text(encoding="utf-8")
        self.assertNotIn("优先读取 WMX", text)
        self.assertNotIn("WebMatrix V5", text)
        self.assertNotIn("wmx-bill-analysis-report", text)
        self.assertIn("本环境没有 WebMatrix", text)


if __name__ == "__main__":
    unittest.main()
