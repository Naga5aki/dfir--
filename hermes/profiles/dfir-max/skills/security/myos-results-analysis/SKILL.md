---
name: myos-results-analysis
description: Use when MYOS已有取证结果需二次分析、查询或关联；含手机（含 iOS 备份/钥匙串）与计算机（电脑/E01/磁盘镜像、BitLocker、VHD、远程桌面、VeraCrypt、Tor、回收站）检材.
---

# MYOS Results Analysis Skill

对 MYOS／超级取证大师已经完成的取证结果做二次关联分析。优先查询已有结果；本技能不授予重新取证、解密、覆盖索引或修改原始证据的权限。

## 二次分析第一跳

先读已有索引，再补一条缺口。不要重跑取证，不要调用 `ges`。详细卡片见 [myos-secondary-card.md](references/myos-secondary-card.md)。

1. 电脑题先读 `notes\device_map.computer.summary.txt`。手机题先读 `notes\device_map.myos.summary.txt`。摘要赛名必须和题面一致，不一致就丢掉，改 `query_open_cases` 按赛名锁定。没有索引才调用概览，落盘后不要整份读回上下文。电脑和手机分开：电脑第一跳是插件库 `.mfs`；手机第一跳是 `appMfsPath`、`apklist.mfs`、`MApps.mfs`。不要把 `Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN` 用到手机题。iOS 备份（`Platform/DeviceInfo`、钥匙串、备份密码）不要用 Android 的 `data\data`，也不要读 `myos_mount.json`；先 `skill_view` `ios-backup-ctf`。
2. 一次只补一个缺口。`.mfs` 先 `sqlite_master`，再一条带 `LIMIT` 的 `SELECT`。禁止 `PRAGMA table_info`。`not authorized` 先核对 caseId 和 mount，不要原样重试。
3. 搜索命中、文件名、插件标签只是线索。没有当次 `sqlite_query` 或 `query_current_node_data` 回执的句子写成“未取到”，不要写成不存在。同一分支两次零命中就换表或写 pending。
4. `quick_search_content` 是有界文件搜索。`global_search_content` 会建异步任务，只提交一次，然后 `query_task_status`。不要用它开局。`create_file_index_task`、`decrypt_partition`、`restart_computer_forensics` 会改状态；二次分析请求本身不是授权。
5. 原始盘用 `query_device_mount_path`。嵌套 VM 仍走现有 `myos_nested_vm.py`，先 `--dry-run`，不要和宿主时间线混写。浏览器密码只用现有 `chrome_login_decrypt.py`。
6. 角标写成 `caseId + materialId + dbPath + 表名 + 查询 + 行`。不默认第一条案件。部分结果不是完整结果。事实、推断、待核验分开。原始检材只读。
7. 工具短名只作索引。调用前看 `tool_search`，保留 `_<hash8>` 后缀，禁止把短名直接当调用名。解题只提交答案，不写笔录，不写 writeup。
8. 题面是独立流水或账单文件、没有 MYOS 插件库时，不要 `sqlite_query`。交接 `dfir-pcap` 的 `bill-flow-analysis`。

## When to Use

用户指定 MYOS 案件、检材、设备、节点、文件内容或时间线，需要查询与关联已有结果。新增采集和维护操作须另有明确指令。

## Prerequisites

- 使用 `dfir-myos` 或 `dfir-max` 已配置的 `myos-forensics` MCP；不能假设其他 profile 有此服务器。
- 先取得用户指定的案件标识和分析目标；不默认打开最近案件或遍历全部案件。
- 工具名以当前会话发现的 schema 为准。下表用原始工具短名，不能据此拼接截断或哈希后的调用名。

## How to Run

使用 `skill_view` 加载本技能；查看目标工具 schema，再按案件、检材、节点逐层缩小范围。服务缺失或业务健康失败时报告缺失依赖；不自动重启 MYOS。

## Quick Reference

| 能力层级 | 原始短名示例 | 边界 |
|---|---|---|
| 健康与查询候选 | health_check_dbus、query_open_cases、query_materials、query_device_info、query_current_node_data、sqlite_query | 先核对参数与当前实现；schema 注解不能证明绝对只读 |
| 案件/挂载状态 | open_case、load_case | 会改变业务状态或挂载；仅在用户指定目标且需要时执行 |
| 嵌套 VM 注册 | add_image_material、add_disk_material、add_file_collection_material | 会新增检材；只注册 VMDK 后 load_case 只读挂载，不提交重新取证任务 |
| 后台搜索 | global_search_content | 创建异步任务；不得当普通同步读取无限重试 |
| 索引写入 | create_file_index_task | overwrite 默认 true；不得为“搜索更方便”自动创建、覆盖或重建 |
| 解密/重新取证 | decrypt_partition、restart_computer_forensics | 用户须明确授权该操作及目标、结果目录；二次分析请求本身不构成授权 |

## Procedure

1. 确认案件唯一标识、检材范围、时区和问题。缺目标时先询问，不扫描案件根目录。
2. 查询已有概览与必要节点；先选少量字段、明确时间范围和有界返回。能关联现有结果时不重做采集或全盘搜索。
3. `query_materials` 的 `includeDetail` 默认保持 false；手机概览在 schema 支持时显式 `includeRawJson=false`。不主动索取 passwords、令牌或密钥；不得原样写入回答、日志或报告。
4. `sqlite_query` 仅用于目标案件的有界 SELECT；不尝试写语句、ATTACH、PRAGMA 修改或绕过只读限制。按实际 schema 提供参数，不猜数据库路径。个别 `.mfs`（如 Platform.mfs）对 `PRAGMA table_info` 返回 `not authorized`：不要重试 PRAGMA 变体，改走 `SELECT name FROM sqlite_master WHERE type='table'` + `SELECT * FROM <表> LIMIT 1`（看行键取列名）再写条件。
5. 概览/总览类大 JSON 会截断：先落盘 `notes\overview.raw.json` 再分段读，重点找 sqliteQueryHints；不要整段灌上下文。
6. 后台任务只提交一次，记录 taskId，以 `query_task_status`／`wait_task_completion` 有界跟踪。超时先确认既有任务状态，不重复提交索引、解密或取证。
7. 区分原始事实、工具派生结果和分析推断，记录案件/检材/节点标识、时间范围、查询条件与证据定位。中文输出；秘密只给必要的掩码或存在性结论。
8. 挂载根层级随检材而异（tar userdata 直挂 vs 完整镜像）：拼路径前先 `ls <root>/data` 确认 App 私有目录是 `<root>/data/<pkg>/` 还是 `<root>/data/data/<pkg>/`，再拼具体路径；不要假设固定层级。

## Computer forensics methodology (keyword-driven)

题面原文压过本节和 [computer-forensics-framework.md](./references/computer-forensics-framework.md) 里的例题。每轮第一跳读题面文件。用户说「未动的题」时，pending 里的 VHD/BAT/偏移计划作废。`sqlite_query` 报 `not authorized` 且语句是 `PRAGMA` 时，改 `sqlite_master` + `SELECT * LIMIT 1`，不要为此 `open_case`。题面出现 BitLocker、VHD、远程连接、VeraCrypt、Tor、回收站、登录失败时，先读 [windows-computer-paper.md](./references/windows-computer-paper.md)，不要用 Linux 开关机表或「成功接收到公网」开局。

1. **拆题**：抽实体（人名/手机号/邮箱/域名/IP/哈希/版本）、工件（开关机/USB/浏览器/微信/远控/文档/音频）、时间（题面时间戳/时区）、格式（单选/多选/简答/选项原文）、检材号五类关键词。
2. **选层**：L1 MYOS 插件库（最快）→ L2 原始文本/配置/日志 → L3 二进制/加密容器（VMDK/Chrome Login Data/keyring/ZIP/图片/音频）→ L4 有界全盘检索（最后手段）。
3. **搜词**：先精确值（哈希、手机号、域名、题面原词），再同义词/英文/包名/字段名；SQL 用 `sqlite_master` 定位表和列，再 `LIKE '%kw%'`；文件用 `grep -r -l -m1 --include=...`；二进制用 `grep -a -b`/`strings`；每次记录「范围 + 命中文件/表 + 字段」。可先用 `computer_keyword_search.py --question "<题面>" --notes <notes> --root <Root> --execute --timeout 60` 生成关键词计划和有界命中。
4. **验证**：至少一个原始字段或两个独立来源；选项题先看选项是否与证据一致；时间戳换算时区；区分观察/推断。
5. **收口**：写 pending（答案/证据/已排除/下一轮）；解题阶段只提交答案，**不写 writeup**；用户明确要求计分/复盘时再补。

详细题型矩阵、搜索命令和典型链式题见 [computer-forensics-framework.md](./references/computer-forensics-framework.md)。2025FIC 检材三的答案/候选/止损点见 [2025fic-computer.md](./references/2025fic-computer.md)（仅该案；提交前仍要原始复核）。

关键词纪律：两次零命中就换分支（OCR / 加密库 / 嵌套 VM / 文档解析），不要换拼法重试；每次 `timeout`、`-m`、`--include`、`maxdepth`；命中即停；同一题最多试 2 个候选。

## Computer forensics fast path (电脑/E01)

适用：用户指定“电脑/计算机/检材三/E01/VHD/raw 镜像”，且 MYOS 已有计算机取证结果。先读已有 `notes/device_map.computer.summary.txt`，不要为了开局调用概览。索引缺失时才用 `query_computer_forensics_results_overview(caseId)` 一次拿到 `integrateForensicsDatabases` 和 `sqliteQueryHints`，落盘 `notes/overview.computer.json`，再用 `myos_computer_compact.py --notes <notes>` 生成摘要。不要把 70KB 概览分段反复读。

查询顺序：

1. 选插件库 → `sqlite_query` 查 `sqlite_master` 一次 → 一条有界 SELECT。`.mfs` 只能走 MCP；不要用 python sqlite3 打开。
2. 题型→库：
   - 开关机：`Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN`；交叉 `/var/log/wtmp`（384B utmpx，u32 tv_sec@340）、`boot.log` fsck 头、syslog `Booting paravirtualized kernel`。题面“最后一次开机”可能指工具表里最后一个完整会话，不等于最新内核 boot；四源不一致且选项不含真实值时，按选项一致值或问用户一次，不要继续烧轮次。
   - USB：`Linux_UsbInfo` / `Win_USB`。
   - 微信：`Win_WeChat.mfs`（Linux 微信可能只有账号/文件/图片，无消息）；版本查 `Linux_InstallSoftWare` 或 `apt list --installed`。
   - 浏览器密码：`Any_Chrome`/`Any_ChromiumBrowser` + 钥匙环（常来自手机笔记）；自动取证密码记录可能只有账号。原始 Chrome `Login Data` 的 `v11` 需 GNOME Keyring：`python chrome_login_decrypt.py --login-data <Login Data> --keyring <默认密钥环.keyring> --keyring-password-stdin`（钥匙环密码从 stdin 传，不上 argv）；脚本内部取 `Chrome Safe Storage` → PBKDF2-SHA1 → AES-128-CBC。
   - 文档：`Any_OfficeMetaInfo` 只有元数据无正文。
   - 文件哈希/文件名：`FSData.mfs` / MYOS 哈希检索；不要全盘算哈希。
   - 远控：仅当题面出现向日葵/sunlogin/todesk/远控软件。`Linux_InstallSoftWare` + `sunlogin*` 轮转日志；按题面时间戳匹配，日志内“成功接收到公网”后是对方公网 IP:port，**优先提交该原句**；不要把同一 IP 的相邻端口、局域网 IP、P2P/relay 服务器当答案；已错 2 个候选就停下复核字段语义。题面只写「远程连接/远程桌面」时改查 `Win_RemoteDesktopInfo`，禁止先读向日葵日志。
   - Windows 试卷（BitLocker 恢复密钥、VHD 盘符、VeraCrypt、邮件附件、Tor 历史、回收站删除时间、照片 GPS、登录失败次数）走 [windows-computer-paper.md](./references/windows-computer-paper.md)。邮件查 `Any_SingleMail` 的 `IP_ADDRESS`/`FILE_MD5`；邮件照片的 GPS 读附件本体 EXIF；4625 的账号在 `POST_DATA`。VHD 盘符查挂载记录或只读挂载副本，不要手解 BAT。同一题连续两次无新字段就写 UNKNOWN，做下一道不依赖它的插件库题。
3. 原始文件：`query_device_mount_path(materialId)` → `/c/osmap/.../Root/PartitionN`。**不要用 `myos_mount.json` 的根**（可能指向手机检材）。先看数据盘 `Partition4/home/<user>`、`文档/桌面/下载`；禁止对 13GB 文档树做全量 grep。命中 `我的测试机/`、`虚拟机/`、`.vmware/`、`*.vmdk` 时按嵌套 VM 处理：先 `python myos_nested_vm.py --case-id <id> --vmdk <vmdk> --dry-run` 看计划，确认后 `--yes`（内部 `add_image_material`→`load_case`→`query_device_mount_path`）；不要提交重新取证任务。在 VM 内找便签/浏览器/微信；便签库 `content` 列的 `data:image/...;base64,...` 复制为 PNG 再 OCR。
4. 文件伪装：`important.docx` 可能是 ZIP（`PK\x03\x04`），解出 XML 后看 `FFD8FFE0`/JFIF 改 `.jpg`；先复制副本，原件只读。音频题先转写；长音频有异常静音分段时取每段首字连读（藏头/谐音）。
5. 速度：一题一进程；题面从 `questions-*.txt` 读，不要逐题 `get_question`；概览只读一次；连续 2 次无新证据就收口写 pending。

## Pitfalls

- 当前精选 22 项包含写入与状态操作；不把它称为只读白名单。
- 不移动 MYOS 管理的 FSData.mfs、dev 或案件数据库；不在原始证据旁生成报告。
- 不自动增加工具、安装软件、重启取证、重建索引或联网补数据。
- 未核实任务写入位置和原件保护方式时，停止该有副作用步骤并说明未知项。

## Verification

结论能回溯到指定案件的具体结果；原件未因本次分析被修改；输出位于用户认可的分析目录。没有结果时报告查询范围和限制，不把“未查到”直接等同“未发生”。
