---
name: hermes-environment-audit
description: Use when 需核查当前Hermes profile的工具、MCP与依赖.
version: 1.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, mcp, environment, inventory, operations]
    related_skills: [hermes-agent, ctf-misc]
---

# Hermes 环境能力盘点与 MCP 运维（SecurityLab）

DFIR 复核以 `hermes -p <profile> config path` 对应文件为准。本文历史清单不是当前注册/健康证明；不修改未获授权的其他 profile，不恢复已删除 hook 或脚本。

环境级 workflow：把"当前可调用的工具 / MCP / skills"盘清（数量 + 逐名 + 实时状态），用实测判定"可调用"，缺件时给出恢复路径。中文产出。

## When to Use（触发）
- "列出/核查当前所有可用的工具、MCP、skills"、环境状态快照
- MCP 工具集整会话缺失（`tool_search` 无该来源）、调用报 unknown tool / `transport is down`
- 换机/迁移后核对 MCP 是否仍可用（注册≠可用）
- 判断某服务器"注册 ≠ 真的可用"

## 盘点流程（三层交叉，缺一层不出结论）
1. **注册表真相**：以 `hermes -p <profile> config path` 指向的 config.yaml 为准，检查 mcp_servers/hooks；.env 只检查变量名和是否存在，绝不打印值。执行 `hermes -p <profile> mcp list`、`hermes -p <profile> mcp test <name>` 与 `hermes -p <profile> hooks list`，不能用 default 的状态替代目标 profile。
2. **会话侧枚举**：直接工具=当前工具面；延迟工具用 `tool_search` 取实时快照——返回体 `available_sources` 即各来源**实时工具计数**、`total_available` 为总数（直接引用，勿手拼）；`skills_list` 出 profile 级技能全表。
3. **活性验证**：端点响应、工具注册、业务就绪分开记录。HTTP 401 仅证明端点响应；stdio 进程存在也不证明后端可用。只对已确认无业务副作用的健康工具作真实调用；没有安全调用或目标未就绪时明确标为未验证，不为验收打开案件、建索引或采集。

## 本环境各 MCP 前置件（快照，易变项以实测为准）
| 服务器 | 前置 | 缺失时现象/处理 |
|---|---|---|
| ctf-misc-arsenal | 非六套 dfir 当前基线；旧配置/旧脚本只作历史资料 | 不自动恢复或执行旧 hook；先核对目标 profile 的实际配置和用户授权 |
| myos-forensics | **必须先启动 `D:\MYOS\Client\bin\ForensicDesktop.exe`** | 已注册≠可用；**MYOS 未运行时不要调 `health_check_dbus`**（失败即令 MCP 进程退出）；先查进程再调用 |
| docker-security | 需 Docker Desktop **引擎**运行（用户级安装：`%LOCALAPPDATA%\Programs\DockerDesktop`，不在 Program Files） | test 报 "Connection closed" / `docker mcp profile ls` 报 "Docker Desktop is not running" = 待启动非未注册。启动 `Docker Desktop.exe` → 有界轮询 `docker info` 就绪（就绪即返回，勿盲等）→ `hermes mcp test docker-security` 复核（实测 10 工具） |
| cyberchef | 无（npx 随会话拉起，无外部程序） | 冷缓存首连可能超时一次（npx 首次下载），重试/新会话自愈；配方库 `work\cyberchef\recipes.json` |
| wiremcp | 无（node 随会话拉起；依赖 PATH 中 tshark，主路径 4.7.1 实测可解析） | tshark 不在 PATH 时工具报错——检查用户 PATH 含 `D:\CTF_Misc_Tools\流量分析\Wireshark`；记录见 `wiremcp-mcp-setup.md` |
| memforensics | 无（venv 随会话拉起；自带 vol3 2.28.2 与 memoxide 引擎二进制，不依赖外部程序） | 引擎异常时 `memory_get_status` 报 `binary_available=false`；重建见 `memforensics-mcp-setup.md` 与 `scripts/build-memoxide-windows.sh` |
| ida | 当前 dfir-re/dfir-max 使用官方六工具：list_databases、open_database、execute_python、reference、save_database、close_database；可连接 GUI 数据库或使用 headless idalib | 当前 MCP 为 127.0.0.1:8737/mcp；不使用旧 13337/check_connection/get_metadata 路线；先读 ida-reverse 并核对实际 schema |
| jadx | 检查 127.0.0.1:8650 插件后端及已加载的目标 APK；插件/server 版本以实际安装信息为准 | MCP 注册不等于插件就绪；未启动时报告依赖缺失，不自动启动 GUI 或安装插件 |
| github | **静态 PAT**：profile `.env` 的 `GITHUB_MCP_TOKEN`（config 里 `${...}` 展开；勿打印值） | 令牌过期→test 报 401 "credential expired"：用户到 `github.com/settings/personal-access-tokens/new` 造新令牌（读权限即可），替换 `.env` 行内值。**换值后运行中的后端仍持旧值——test 通过 ≠ 会话可用，须再走"值变更重载"（见坑 1 / `mcp-server-recovery.md` E 节；脚本 `scripts/reload_mcp_gateway.py`），实测重载后注册 26 只读工具。** **勿走 OAuth**：远程 GitHub MCP 官方不支持 DCR，`hermes mcp login` 对静态令牌服务器直接报 not configured for OAuth。细案见 `references/mcp-server-recovery.md` |
| chrome-devtools / playwright / semgrep / snyk / context7 | 随会话建立连接 | — |
| sequentialthinking | 无（npx 随会话拉起；纯内存推理，无外部依赖/文件） | 冷缓存首连可能超时一次（npx 首次下载）；推理辅助（非分析工具），思考历史不跨会话 |

完整注册记录：`D:\Hermes\SecurityLab\{ctf-misc-arsenal,myos-forensics,cyberchef,wiremcp,sequentialthinking,memforensics,ida,jadx}-mcp-setup.md`；本地 CLI 工具链以当前 profile 和实际依赖检查为准；旧 memory/local-tooling.md 引用未验证，不恢复缺失文件。

## 执行与沟通约定
- **"帮我执行"= 先穷尽可编程路径**，次序：(a) 证伪需求——运行时是否已有自动机制覆盖（如回合间 MCP 刷新）；(b) CLI / 配置 / 进程操作；(c) **本地 API / RPC**——桌面 UI 按钮背后多是 gateway JSON-RPC（如 /reload-mcp = `reload.mcp`），可经本机 WS 直发代替用户操作（`references/mcp-server-recovery.md` E 节）；(d) 最后才是 UI 驱动（`references/desktop-automation-fallback.md`）。确属只有用户能做的（登录、造令牌）→ 给**最小步骤**：文件 + 行号 + 一条可复制命令，不写教程长文；并把文件**在目标行替用户打开**（`notepad++ -n<行号> <文件>`；无则该用 `notepad`）——用户只需粘贴 + 保存。
- "安装 / 修复"类动作，首句写明**装进哪个既有环境**（例："往已有 WSL 发行版里补工具，不新增系统"）——否则易被质疑重复安装。

## 产出与存档
- 会话内：**先总览表（类别/数量/状态）再逐名清单**；每条"可用"标注判定依据（已连接 / 需先启动 / 不可用）；用户要"所有"就列全，勿因简短省清单。
- 全量归档到 `D:\Hermes\SecurityLab\reports\`（含快照时间 + `hermes --version` + 注册名级细节），聊天里用 `MEDIA:` 卡片交付。

## 迁移/换机后的 MCP 复核
- 先 `hermes mcp list` 确认注册项齐全，再逐个 `hermes mcp test`；注册存在不等于后端可用。
- 恢复外部工具池时不要排除 `node_modules`（WireMCP 依赖它）；`.venv` 不要复制，按目标机路径重建。
- IDA/jadx/MYOS 的 GUI 前置件受盘符和用户名影响；用迁移脚本的 `--target-root/--tools-root/--myos-root` 修正后再测。完整流程见 `D:\Hermes\SecurityLab\migration\README.md`。

## 坑
1. **挂载语义——先证伪"需要 /reload-mcp"**：桌面版**每回合间自动刷新** MCP（`agent/turn_context.py::_refresh_mcp_tools_between_turns` → `refresh_agent_mcp_tools`）：服务器"当初连不上、后来可用"时下个回合**自动并入**，无需 /reload-mcp、无需新会话；只有"增/删/改 MCP 配置"才需要 reload。**例外（实测）：改的是 `.env` 里的值**（如换令牌）时，自动刷新只重发布注册表——不重连、不重读 `.env`，后端进程仍持旧值（401 重试循环持续）；须发 `reload.env` → `reload.mcp` 重载（脚本 `scripts/reload_mcp_gateway.py`，配方见 `references/mcp-server-recovery.md` E 节）。验证并入=对比 `tool_search` 的 `total_available`/`available_sources` 计数（实例：18 源/268 工具 → 19 源/324 工具，恰 +56=arsenal），再以 `tool_describe` 取到 schema 才算真并入；首查未见过渡态勿判失败。
2. `tasklist` 中文输出 GBK 乱码，只认 ASCII 进程名；按路径过滤用 PowerShell：`Get-Process | Where-Object {$_.Path -like 'D:\MYOS*'}`。
3. `tool_search` 查询 = "服务名 + 动作/对象"；没命中先换词重试，再下"不可用"结论。
4. 报告区分三态：已注册未连接 / 已连接未就绪（前置程序未启动）/ 不可用——别把"未启动"报成"没有此能力"。
5. bash 与**原生 exe**（python、cua-driver 等）共享文件必须用规范 Windows 路径（`C:/Users/<u>/AppData/Local/hermes/cache/scratch/…`）——MSYS 的 `/tmp` 原生程序读不到（FileNotFound）；连 stderr 一起落盘用 `> f 2>&1`，写成 `2>&1 > f` 会把 stderr 留在终端。

## 支持文件
- `scripts/mcp_http_probe.py` — 本地 HTTP MCP 独立探针（initialize → tools/list；token 按 key 名从 Hermes `.env` 读取、不回显；JSON/SSE 自适应）。
- `scripts/reload_mcp_gateway.py` — 值变更重载：自动发现本机 hermes 后端（`netstat` 定位端口 + 从根页取 `__HERMES_SESSION_TOKEN__`），经 `/api/ws` 发 `reload.env` → `reload.mcp`；`--dry-run` 只探测；需 `websockets`。
- `references/mcp-server-recovery.md` — 按故障类型的 MCP 恢复配方（认证过期/静态 PAT、OAuth 与 device 流、无 DCR 处置、前置引擎未起、恢复后并入验证、OAuth 元数据探测）。
- `references/desktop-automation-fallback.md` — cua-driver CLI 从终端后台驱动桌面（兜底通道；已验证/未验证边界与纪律）。
