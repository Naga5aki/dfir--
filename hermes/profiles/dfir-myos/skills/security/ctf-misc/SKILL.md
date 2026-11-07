---
name: ctf-misc
description: Use when CTF杂题、RSA、编码、隐写或压缩包需本地工具分析.
---

# 本地 CTF 杂题

## 当前六套 DFIR 的直接决策

六套 DFIR 没有 CTF Misc Arsenal、CyberChef 或 Sequential Thinking MCP。`ctf-arsenal-ensure.py` 与旧 pre_tool_call hook 已被用户删除/禁用，不恢复、不执行，不修改令牌或其他 profile。

对于“能否恢复旧 Arsenal hook”这个问题，直接回答“不恢复，使用当前已有本地工具或小脚本”。本节已经给出完整结论，不需要读取旧 Arsenal 参考手册来再次确认；不要重复读取已经读过的技能或参考。历史资料不能覆盖当前能力边界。

## 最小流程

1. 确认授权样本、题型、已知线索、独立输出目录与时间预算。没有样本只给分析路线，不扫描 cases 根目录、不伪造 flag 或输出。
2. 先确认当前 profile 的 terminal backend（dfir-max 为 local Windows；其他 profile 可能是 Kali SSH）。验证命令/依赖与挂载路径；远端后端不能直接执行 Windows `D:/...exe`。缺组件时报告，不自动安装、下载或切换后端。
3. RSA/编码先明确参数与编码层，用已有 Python/数学工具或短脚本有界验证。隐写、压缩包按格式/元数据线索选一条最小路线；破解先限制字符空间和时长，不默认启动大爆破。
4. 原件只读，必要时前后 SHA-256；派生文件只写认可的输出目录。工具“成功”需格式自检、对照/负控制，结论回到字节、偏移和可复现参数。
5. 输出中文区分观察、推断与未验证项；缺工具/符号/路径时给明确限制，不能把旧注册记录当成当前可用证明。

## 专项分流

- PCAP/WebShell/隧道：`wire-toutetu`，默认离线；不自动实时抓包或联网查信誉。
- 内存：`memory-forensics-local`，先满足离线/符号前提，不默认 triage 或凭据导出。
- EXE/ELF/so：`ida-reverse`；APK Java/Smali：`android-malware-analysis`，按当前 GUI/服务实际状态使用。
- MYOS 既有结果：`myos-results-analysis`，重建索引、解密、重新取证不是普通查询。

## 按需参考与脚本

仅在实际题目需要某一细节时读取对应参考，不要为一般路线或旧 hook 问题批量加载：

- 工具接入 L0→L4、历史 Windows 工具经验：`references/ctf-misc-local-workflow.md`
- Windows 编码/引号问题：`references/windows-toolchain-pitfalls.md`
- 合成格式闭环：`references/synthetic-sample-recipes.md`
- OOXML 结构：`references/ooxml-docx-inventory-extraction.md`
- 网格载体：`references/equidistant-grid-extraction.md`，`scripts/grid_extract.py`
- 工具输出有效性：`references/output-validity-triple-gate.md`
- 已授权 VeraCrypt 类容器：`references/veracrypt-offline-unlock.md`，`scripts/vera_unlock.py`
- 已有字节重组工具：`scripts/crc32_invert.py`、`scripts/interleave_reassemble.py`

调用脚本前按当前安装的 skill-root 与 Kali 实际路径解析，先用良性最小输入验证；不把技能源目录作为案件输出目录。
