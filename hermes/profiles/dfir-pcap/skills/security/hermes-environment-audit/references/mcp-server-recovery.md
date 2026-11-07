# MCP 服务器恢复配方（按故障类型）

先诊断，别猜：
1. `hermes mcp list` — 注册 / enabled / transport 一览。
2. `hermes mcp test <name>` — 真实连接 + 工具清单；**失败文本即分类依据**（输出中凭据自动打码）。
3. 按文本分类：`401 / credential expired` → 认证过期；`Connection closed` → 前置进程/引擎未起；transport 报错 → 命令或 URL 配置错。

## A. 认证过期（静态令牌服务器）

例：github 用 `${GITHUB_MCP_TOKEN}`（位于 `mcp_servers.github.headers.Authorization`，值在 profile `.env`；改前只 `grep -n` 定位行号、不打印值）。

1. 用户到 `https://github.com/settings/personal-access-tokens/new`（fine-grained，读权限即可：Contents / Issues / Pull requests = Read-only；经典版勾 `repo`）生成新令牌。
2. 替换 `.env` 对应行内值，保存。
3. `hermes mcp test github` 复核（新进程读新值；通过 = 新令牌本身正确）。**但这不会让运行中的后端生效**——后端进程仍持旧值、重连循环持续 401；并入会话还须走 E 节"值变更重载"。

**别再尝试的弯路**：`hermes mcp login github --flow device` 对静态令牌服务器报 "not configured for OAuth (auth=None)"；GitHub 远程 MCP 官方明确**不支持 DCR**，OAuth 需自建 OAuth App（含 client_secret）+ 回环回调——成本远高于换 PAT（PAT 是 GitHub 官方文档认可的替代方式）。

## B. OAuth 服务器（config `auth: oauth`）

- 登录：`hermes mcp login <name> [--flow device|browser]`；服务器侧 `oauth.flow: device` 可固化偏好。device 流=零弹窗首选：打印验证 URL + 用户码，任意设备批准，CLI 轮询完成；`oauth.timeout` 控等待上限（默认 300s）。
- **无 DCR 的授权服务器必须配 `oauth.client_id`**（必要时 + `client_secret`）——源码 `tools/mcp_oauth_device.py::_register`：无 client_id 且无 `registration_endpoint` 时报 "configure oauth.client_id"。
- CIMD（client_id 写元数据文档 URL）仅当服务器 advertise `client_id_metadata_document_supported: true` 才启用，否则退回 DCR。
- 令牌存放：`~/.hermes/mcp-tokens/<server>.json`（命名 profile 在 `profiles/<name>/mcp-tokens/`）。
- 端点能力探测（判断某 MCP URL 支持何种 OAuth）：
  1. `curl -i -X POST <mcp-url>`（带一个 initialize 假 JSON）→ 401 挑战里的 `resource_metadata` URL；
  2. `GET <.../.well-known/oauth-protected-resource/<path>>` → `authorization_servers` 列表；
  3. AS 元数据走 RFC 8414 **路径插入式**：`https://<host>/.well-known/oauth-authorization-server/<path>`（例：github 的 AS 在 `/login/oauth`；查根路径会 404）；
  4. 看 `registration_endpoint`（有=DCR 可用）与 `grant_types_supported`（含 `device_code` 才能 device 流）。

## C. 前置引擎 / 进程未起（test 报 "Connection closed"）

- **docker-security**：命令为 `docker mcp gateway run --profile security_lab`，需 Docker Desktop 引擎。本机为**用户级安装**：`%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe`（不在 Program Files）。拉起 → 有界轮询 `docker info` 就绪（`for i in $(seq 1 40); do docker info >/dev/null 2>&1 && break; sleep 5; done`，就绪即返回）→ `docker mcp version` 看插件 → `hermes mcp test docker-security`（实测连通、10 工具：mcp-find / mcp-add / mcp-exec / code-mode / fetch_content 等）。
- **ctf-misc-arsenal**：跑 `agent-hooks/ctf-arsenal-ensure.py` 拉起；测时勿带 `HERMES_DISABLE_LAZY_INSTALLS=1`（挡 mcp HTTP 组件懒安装→伪报 "streamable_http not available"）。
- 其余前置件（MYOS / IDA / jadx 等）见 SKILL.md 前置表。

## D. 恢复后的并入验证（"/reload-mcp 之问"）

- 桌面版**每回合间自动刷新**（`agent/turn_context.py::_refresh_mcp_tools_between_turns` → `refresh_agent_mcp_tools`，preserve_prefix）：服务器"当初连不上、后来可用"→ **下个回合自动并入**；`/reload-mcp` 仅对 "增 / 删 / 改 MCP 配置" 必要（且会重建工具面、使提示词缓存失效）。
- **例外：`.env` 换值**（如令牌轮换）自动刷新不覆盖——它只重发布注册表：不重连（重试循环仍持进程内旧值），也不重读 `.env`；须走 E 节值变更重载。
- 证据式验证：`tool_search` 的 `total_available` / `available_sources` 计数对比（实例：18 源/268 工具 → 19 源/324 工具，恰 +56 = arsenal）；再对具体工具 `tool_describe` 能拿到 schema 才算真并入。
- 若确需从 UI 触发会话内命令（无程序化通道且自动机制不覆盖），见 `desktop-automation-fallback.md`（最后手段）。

## E. 值变更重载（`.env` 换值后让运行中后端生效）

**症状**：替换 `.env` 令牌值后，`hermes mcp test <name>`（新进程）通过，但会话里该 MCP 工具集始终不出现；后端日志每几秒一次 401 重试（如 GitHub `credential expired`）。

**机制**：桌面后端是 `hermes serve` python 进程（随机 127.0.0.1 端口）。两种"刷新"别混淆——
- 回合间自动刷新（`refresh_agent_mcp_tools`）= 把**已连接**的注册表重发布给会话；
- 值变更必须走 gateway RPC：`reload.env`（后端重读 `.env`）+ `reload.mcp`（拆除全部 MCP 连接并重发现，"for every live session"）。

**步骤（loopback 模式，实测）**：
1. 定位后端：`netstat -ano` 找 127.0.0.1 LISTENING 端口（对应 python PID）；`curl http://127.0.0.1:<端口>/` 应回 "Headless backend (hermes serve)" 页，内嵌 `__HERMES_SESSION_TOKEN__`（`__HERMES_AUTH_REQUIRED__=false` = loopback 模式）。
2. 发 RPC（一键：`scripts/reload_mcp_gateway.py`；或手工）：`ws://127.0.0.1:<端口>/api/ws?token=<token>`（缺 `?token=` 直接 403；子协议可选）→ `reload.env {}`（回 `{"updated": N}`）→ `reload.mcp {"confirm": true}`。
3. REST 旁证通道：`Authorization: Bearer <token>`（如 `GET /api/mcp/servers` 读服务器清单）。

**验证（勿只看回包）**：`reload.mcp` 异步执行，客户端可能 15–30s 等不到回包（正常）。以证据为准：
- `logs/agent.log`：`MCP server '<name>': registered N tool(s)`（随后其余服务器依次重注册亦然）；
- `tool_search`：会话目录是实时的——新工具**本回合内**即可检索/调用（无需重启、无需用户手发 /reload-mcp）。

**边界**：
- `reload.mcp` 波及**所有**活会话的全部 MCP（各服务器数秒内自动重连重注册，属预期）；
- 契约：`apps/shared/src/gateway-contract.openrpc.json` 的 `ReloadMcpParams {session_id?, confirm?, always?, rev?}`——缺 `confirm` 可能回 `confirm_required`；`always` 会持久化用户设置，非用户要求勿带；
- gated 模式（`__HERMES_AUTH_REQUIRED__=true`）认证不同：WS 用一次性 `?ticket=`（约 30s TTL）或 `?internal=`，legacy `?token=` 被拒；
- 桌面 UI 对照：`/reload-mcp` = 同一个 `reload.mcp` RPC（桌面可用）；`/reload`（重读 env）为 CLI-only——"让用户发 /reload"不可行时，直发 RPC 是正路。
