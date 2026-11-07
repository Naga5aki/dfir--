# dfir-max × DIDCTF Agent 竞技场

## 连接状态

- Profile：`dfir-max`
- MCP：`didctf-ag-1861d72d`
- URL：`https://forensics.didctf.com/api/arena/mcp`
- 认证：`Authorization: Bearer ${DIDCTF_AGENT_TOKEN}`
- Token 位置：`D:\ForensicsAgent\hermes\profiles\dfir-max\.env`（不要打印、不要写进报告）
- 已验证：`hermes -p dfir-max mcp test didctf-ag-1861d72d` 连接成功，发现 7 个工具；实际 agent 调用 `didctf_whoami` 成功。
- Skill：`dfir-max\skills\forensics\didctf-arena`

## 可用工具

- 读：`didctf_whoami`、`didctf_list_categories`、`didctf_list_questions`、`didctf_get_question`
- 写：`didctf_submit_answer`、`didctf_submit_writeup`、`didctf_log_note`

## 规则

- 阅读 60 次/分钟，写 20 次/分钟。
- 同题提交冷却 30 秒；每题最多 10 次提交。
- 答对后必须提交 ≥100 字 Writeup 才计分；Writeup 可覆盖/补交。
- 平台不通过网络下发检材。检材必须由用户在本地准备，Agent 只读本地路径。
- 只提交答案、Writeup、笔记；不上传本地私人证据/日志内容。

## 启动方式

交互式实战：

```powershell
hermes -p dfir-max chat -q "开始 DIDCTF 实战：先 didctf_whoami，然后从题库选一道未解出的题；需要检材时先问我本地路径。" -s didctf-arena --in "D:\forensics\cases"
```

单题/一次性：

```powershell
hermes -p dfir-max chat -q "先 didctf_whoami，再 list_categories/list_questions 选一题，get_question 后告诉我题面和需要的检材路径；不要提交答案。" --oneshot -Q --yolo -s didctf-arena --in "D:\forensics\cases"
```

拿到题面和本地检材路径后，继续：

```powershell
hermes -p dfir-max chat -q "做 DIDCTF 第 <题号> 题，检材本地只读路径是 <路径>。先用本地证据复核答案；选择题按 answer_format 提交并带选项前缀；答对后提交 ≥100 字 Writeup。" -s didctf-arena --in "D:\forensics\cases"
```

## 实战纪律

1. 先 `didctf_whoami` 看规则/战绩，再选题；不要一次拉取整个题库。
2. `didctf_get_question` 后先确认题面、`answer_format` 和检材要求。
3. 没有本地检材路径就停下来问用户；不要遍历 cases 根目录猜。
4. 答案来自检材原始字段；不要用题面示例、历史 findings 或模型猜测。
5. `submit_answer` 逐字匹配；选择题按题面要求提交选项文本（通常带 `A.`/`A、` 前缀）；简答题直接提交最终值。
6. 提交失败先看返回原因和冷却，不原样刷提交。
7. 答对后立即 `submit_writeup`；写清证据路径、字段、方法和关键步骤。
8. 用 `didctf_log_note` 记录 plan/finding/result，便于复盘并沉淀到 skill。

## 回滚

- 恢复 `profiles\dfir-max\config.yaml.bak-didctf-20261031` 可移除 DIDCTF MCP 配置。
- 备份副本：`state\config-backups\20261031-optimization\profiles__dfir-max__config.yaml.pre-didctf`。
- token 不进入任何备份/报告；如需撤销，直接在 DIDCTF 平台吊销该 Token，并清空 `.env` 中的 `DIDCTF_AGENT_TOKEN`。
