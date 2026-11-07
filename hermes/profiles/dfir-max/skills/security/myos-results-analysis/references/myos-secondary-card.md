# MYOS 二次分析卡片

本环境没有火眼 CLI。未接入，不要调用 Goldeneyes:// 角标。二次分析只消费当前会话 `tool_search` 里的 `myos-forensics` 工具。短名不是调用名。

## 阅读顺序

1. 用户指定的案件和问题。缺 caseId 或检材标识时先问，不打开最近案件，不默认列表第一条。
2. 已有 `notes\device_map.computer.summary.txt` 或 `notes\device_map.myos.summary.txt`。
3. 索引缺失时才取概览：电脑用 `query_computer_forensics_results_overview`，手机用 `query_phone_forensics_results_overview`。落盘后分段读 sqliteQueryHints，不把约 70 KB 概览灌进上下文。
4. 一个缺口，一条查询。`.mfs` 只能走 `sqlite_query`。先 `SELECT name FROM sqlite_master WHERE type='table'`，再一条带 `LIMIT` 的 `SELECT`。
5. 原始文件才 `query_device_mount_path`。不要用 `myos_mount.json` 的根。不对约 13 GB 文档树全量 grep。

## 证据记录

每条证据八个字段：`source`、`object`、`time`、`action`、`receipt`、`grade`、`gap`、`handoff`。没有 `receipt` 就没有这条证据。等级只用 E1 静态清单、E2 可定位代码或记录、E3 当次工具回执、E4 至少一条 E2 加一条 E3。插件结果本身不是 E4。

结论强度只用：已确认、高度支持、初步支持、线索提示、待验证。解题提交值不写这些词，也不写 E1–E4。没读到写“未取到”。

搜索命中、关键词、相似度、文件名都只是线索，必须回查当次查询或 `query_current_node_data`。部分结果、非零退出、截断、`source_complete=false` 都不是“未发现”或“完整结果”。

## 题型第一跳

| 问题 | 第一跳 | 禁止 |
|---|---|---|
| 开关机 | `Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN` | 先搜文档树 |
| USB | `Linux_UsbInfo` / `Win_USB` | 用文件名猜设备 |
| 微信 | `Win_WeChat` | 把聊天当已核实事实 |
| 浏览器 | `Any_Chrome` / `Any_ChromiumBrowser` | 抄历史密码；解密只用 `chrome_login_decrypt.py` |
| 文档元数据 | `Any_OfficeMetaInfo` | 用正文关键词代替元数据 |
| 原始盘路径 | `query_device_mount_path` | 猜盘符 |
| 嵌套 VM | `myos_nested_vm.py --dry-run` 后才 `--yes` | 和宿主时间线混写；不要 `restart_computer_forensics` |
| 手机 App | `device_map.myos.summary.txt` 的 `appMfsPath` | 凭记忆写包名；不要 `ls data/data` 开局 |
| 独立流水文件 | 交接 `bill-flow-analysis` | 对表格做 `sqlite_query` |

同一分支两次零命中就换表。不允许第三次扩大同一查询。

## 会改状态的工具

`open_case`、`load_case`、`add_image_material`、`add_disk_material`、`add_file_collection_material`、`create_file_index_task`、`decrypt_partition`、`restart_computer_forensics`、`global_search_content` 都不是只读。二次分析请求本身不是授权。索引任务 overwrite 默认为真，不得为了搜索方便重建。

`global_search_content` 只提交一次，用 `query_task_status` 或有界的 `wait_task_completion` 跟踪。超时先查原 taskId，不重复提交。

## 报告

只有用户要求报告时才按这个顺序写，并且只消费已经归一的证据：

1. 任务范围
2. 案件与检材：编号、路径、授权范围、解析状态
3. 实际调用的工具短名和当次查询
4. 事实
5. 推断
6. 待核验
7. 未覆盖范围
8. 下一步

没有有效回执的句子降级为待核验。报告不是鉴定意见。token 不写入报告。
