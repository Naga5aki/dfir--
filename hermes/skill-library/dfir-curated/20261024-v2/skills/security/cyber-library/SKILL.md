---
name: cyber-library
description: Use when 本地专用技能不足、需检索818社区安全参考库.
---

# Local Security Reference Library

优先当前 profile 的工具和本地专用技能；只有缺少对应方法时才检索社区参考库。无需为问候、概念解释、会话总结或已有充分证据的回答额外搜索。

## Local routes

| 任务 | 按需加载的本地技能 |
|---|---|
| MYOS 已有结果二次分析 | `myos-results-analysis` |
| APK / Java / Smali / JADX | `android-malware-analysis` |
| EXE / ELF / IDA / 原生 so | `ida-reverse` |
| 离线 PCAP / 隧道 / 流量 | `wire-toutetu` |
| 内存 / memforensics / Volatility | `memory-forensics-local` |
| 磁盘镜像 | 按目标系统选择 `windows-loader` / `linux-loader`，未知系统先 `digital-forensics` |
| CTF / RSA / 隐写 / 杂题 | `ctf-misc`；不要统一套用 SQL 注入流程 |

路由 hook 若已提示合适的本地技能，使用 `skill_view` 加载一次即可，不再重复搜索参考库。已加载的技能不重复读取。

## Reference fallback

库是社区项目，不代表 Anthropic 官方认证；其流程不保证适用于当前环境。

- Windows 路径：`D:/ForensicsAgent/hermes/skill-library/anthropic-cyber`
- 已验证的 Kali 路径：`/mnt/d/ForensicsAgent/hermes/skill-library/anthropic-cyber`

检索使用英文工具/证据关键词；通过 `terminal` 的已验证 Kali 后端运行库内 `search.py`，先返回至多 3 个候选，只读最相关的一份 SKILL.md。文件工具若因库在案件工作区外而拒绝读取，不反复重试。

不全文读取 index.json，不批量加载 818 个技能。引用中的安装、live 采集、联网、写入或覆盖步骤不因“命中技能”自动获准；先匹配用户当前任务与已有工具。缺案件/检材路径先询问，不遍历整个 cases 根目录。
