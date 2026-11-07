# DIDCTF MCP 接入 dfir-max（2026-10-31）

## 结果

- 已在 `dfir-max` 配置中增加远端 HTTP MCP：`didctf-ag-1861d72d`
- URL：`https://forensics.didctf.com/api/arena/mcp`
- 认证：`Authorization: Bearer ${DIDCTF_AGENT_TOKEN}`
- Token 仅存放在 `profiles\dfir-max\.env`，未写入 config、报告或本文件。
- 新增技能：`profiles\dfir-max\skills\forensics\didctf-arena\SKILL.md`
- SOUL 增加 DIDCTF 实战流程、限流、Writeup、检材本地路径和禁止上传证据的约束。

## 验证

1. `hermes -p dfir-max mcp list`：`didctf-ag-1861d72d` 已启用。
2. `hermes -p dfir-max mcp test didctf-ag-1861d72d`：连接成功，发现 7 个工具。
3. 直接 MCP 调用 `didctf_whoami`：成功；Agent 为 `dfir`（slug ag-1861d72d），当前 solved/scored/total 均为 0。
4. 实际 `hermes -p dfir-max` 会话中调用 `didctf_whoami`：成功；确认不是只配置了 URL，而是 agent 真正能调远端工具。
5. 未提交任何答案或 Writeup。

## 平台规则（来自 whoami/页面）

- 阅读 60 次/分钟，写 20 次/分钟。
- 同题提交冷却 30 秒，每题最多 10 次提交。
- 答对后必须提交 ≥100 字 Writeup 才计分；可覆盖/补交。
- 检材不通过网络下发；本地准备，Agent 只读路径。
- 只提交答案/Writeup/笔记，不上传本地私人证据。

## 文件

- `profiles\dfir-max\config.yaml`
- `profiles\dfir-max\.env`（token，不打印）
- `profiles\dfir-max\SOUL.md`
- `profiles\dfir-max\skills\forensics\didctf-arena\SKILL.md`
- `docs\DIDCTF实战.md`
- 回滚备份：`profiles\dfir-max\config.yaml.bak-didctf-20261031`，以及 `state\config-backups\20261031-optimization\profiles__dfir-max__config.yaml.pre-didctf`

## 限制

- 还没有实际提交过 DIDCTF 题目答案/Writeup；首个实战需要用户提供本地检材路径。
- 远端工具限流与同题冷却以平台返回为准；不要用脚本绕过。
- 只配置了 `dfir-max`，没有改 `dfir-myos`。
