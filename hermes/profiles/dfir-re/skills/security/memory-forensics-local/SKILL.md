---
name: memory-forensics-local
description: Use when 内存镜像需用本地memforensics或Volatility分析.
---

# Local Memory Forensics Skill

使用已有内存镜像和本地 memforensics／Volatility 做有界分析。优先复用既有结果，不自动采集 live RAM、安装符号或导出凭据。

## 问题到插件

按问题选一个已有 MCP 短名，不默认全量 triage。进程、注入、网络、命令历史、隐藏驱动必须分开写“未检查 / 检查失败 / 本次未发现”。单项插件结果不能写成恶意结论。YARA 只在用户给出规则时扫描。凭据提取不是初筛步骤；LSASS 只有用户点名时才进入，秘密不进聊天。`memory_extract_credentials` 仍不是常规步骤。

## When to Use

内存镜像中的进程、注入、连接、命令历史与落地文件关联；用户明确指定 Volatility 或当前 memforensics MCP。

## Prerequisites

- MCP 位于 `dfir-mem`、`dfir-max`；Kali `terminal` 可作为已授权且路径验证通过的本地 CLI 路线。
- 确认镜像绝对路径、系统类型、已有哈希、分析目标与独立输出目录。未知路径先询问，不扫描 cases 根目录。
- 先检查当前 schema、后端与符号状态。当前 MCP 的 Vol3 automagic 未强制离线，缺 Windows 符号时可能自动联网。未知缓存完整性时，不得初始化镜像或执行会触发 automagic 的插件；先验证离线约束或所需符号已满足。无法确认则报告限制，改用已验证的 CLI `--offline` 路线或等待用户决定。缺组件时不自动下载或改动环境。

## How to Run

通过 `skill_view` 加载，再选择最小必要插件或查询。当前工具名以实际发现为准；不能把旧缓存当实时注册证明。

## Quick Reference

| 目标 | 已有 MCP 短名候选 |
|---|---|
| 已有会话/状态 | memory_list_sessions、memory_get_status |
| 可用插件 | memory_list_plugins |
| 进程/关联线索 | memory_get_process_tree、memory_hunt_process_anomalies |
| 注入/连接/历史 | memory_find_injected_code、memory_find_c2_connections、memory_get_command_history |
| 特定插件 | memory_run_plugin |
| 导出 | memory_dump_process、memory_dump_vad：须另有明确目标与授权输出目录 |

## Procedure

1. 优先复用与同一镜像及哈希对应的既有分析会话。没有已有结果时说明需要创建派生分析结果，并使用用户认可的输出目录。
2. 满足上述离线/符号前提后，再获取镜像/系统基本信息，确认符号和插件兼容性。错误需区分路径、镜像格式、系统不支持、符号缺失和真正无结果。
3. 按问题选择一组小查询，先限制进程/时间/字段和返回量。不要默认 `memory_full_triage`，也不因一次失败反复启动全量分析。
4. 对可疑 PID，关联进程树、命令行、连接、注入与文件线索；异常单信号不足以下恶意结论。
5. `memory_extract_credentials` 不作为常规步骤。用户明确需要时也不在聊天或普通日志里输出秘密原文。
6. 导出、triage、analyze 等可能创建目录和结果文件；原始镜像保持不变。不得将输出目录设为技能源树、镜像原件目录或其他案件。
7. 记录镜像标识、插件/后端版本、查询参数、PID/偏移、时区和证据引用；中文区分观察、推断与限制。

## Pitfalls

- 本地单模型单槽：模型请求串行；不靠多 profile 并发弥补等待。
- Windows 盘符与 Kali 挂载路径需实际验证，不能直接把 `D:/...` 发给远端 shell。
- 服务启动、工具注册不等于符号加载或镜像分析成功。
- 不自动采集 live RAM、下载符号、安装工具或覆盖旧结果。

## Verification

结论可定位到镜像、PID/偏移及具体插件结果；派生文件独立保存，镜像哈希保持不变。失败给出已经验证的原因和可选下一步，不虚构分析结果。
