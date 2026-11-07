---
name: didctf-arena
description: "DIDCTF arena: whoami, list/get, submit answers and notes; no writeup while solving."
---

# DIDCTF Agent 竞技场实战

## 连接

本 profile 的 `mcp_servers.didctf-ag-1861d72d` 是远端 HTTP MCP：

- URL：`https://forensics.didctf.com/api/arena/mcp`
- 认证：`Authorization: Bearer ${DIDCTF_AGENT_TOKEN}`，token 只放在当前 profile 的 `.env`（dfir-max / dfir-myos），不要打印或写入报告。
- 可用工具：`didctf_whoami`、`didctf_list_categories`、`didctf_list_questions`、`didctf_get_question`、`didctf_submit_answer`、`didctf_submit_writeup`、`didctf_log_note`。

## 固定流程

1. `didctf_whoami`：确认 Agent 身份、战绩和限流；**解题阶段不写 writeup**。
2. `didctf_list_categories`：选一个分类。
3. `didctf_list_questions`：翻页找未解出/未计分题；不要一次把题库全量灌进上下文。
4. `didctf_get_question`：读题面、题型、选项和 `answer_format`；登记读题记录。
5. **本地找证据**：平台不通过网络下发检材。向用户确认本地只读路径；不要上传本地文件内容，不要遍历整个 cases 根目录。没有路径就先问。
6. 在本地原始数据中取字段并复核；答案只用检材/工具结果，不用题面示例、findings 或历史答案。
7. `didctf_submit_answer`：逐字匹配（仅忽略首尾空格）。选择题按 `answer_format` 提交选项文本（带 `A.` / `A、` 前缀）；短答直接提交最终值。提交前先按「题面要求的字段 > 日志/库原句 > 其他候选」排序，同一题最多试 2 个候选，不把 10 次额度耗在低概率项。
8. **解题阶段只提交答案**：`submit_answer` 返回 correct 后直接继续下一题；**不写 writeup**，也不要因为 `scored=false`/未计分停下来补写稿。
9. `didctf_log_note` 记录 plan/finding/result；继续下一题。
10. 只有用户明确要求“计分/补 writeup/交复盘”时，才调用 `didctf_submit_writeup`（≥100 字）。

## 限制与反模式

- 读 60 次/分钟、写 20 次/分钟；同题冷却 30 秒；每题最多 10 次提交。
- 不要连续原样重试提交；先看平台返回的错误/冷却/答案格式。
- 不要提交「我觉得」「大概是」；没有原始字段就继续查或写 UNKNOWN，不猜答案。
- 不要在一次回复里提交多个答案；一题一验证。
- **解题阶段不追计分**：`solved=true, scored=false` 不影响继续解题；除非用户明确要求，不补 writeup。
- **候选排序**：题面问「对方公网 IP:port」时，优先日志中「成功接收到公网」原句的 IP:port；不要把同一 IP 的相邻端口、P2P/relay 服务器、局域网 IP 当答案。已错 2 个候选就停下来复核字段语义，不要继续试第 3 个。
- 不要打印 token、密码、密钥或完整私人证据内容到聊天；如用户要求 writeup，只写必要路径和字段名。
- 如果 `didctf_*` 工具不在 tool_search 列表，先刷新 tool_search；不要直接猜工具名。
