# Windows 计算机试卷路由

下文是路由，不是答案。没有当次 `sqlite_query` 或原始文件回执，不得提交。2025FIC 的 Linux 矩阵（开关机、向日葵「成功接收到公网」、嵌套 VMDK）只在题面出现对应词时使用。

## 开题

1. 每轮第一跳读题面原文（用户附件或 `questions-*.txt`）。「继续做题」也先读题面。用户说「未动的题」时，pending 里的 VHD/BAT/偏移计划作废，从还没查过的插件库题开始。
2. `notes\device_map.computer.summary.txt` 的赛名必须和 `query_cases` 当前案件一致。不一致就丢掉，对当前 `caseId` 重跑 `myos_computer_compact.py`。`myos_mount.json` 可能是手机检材，不能当电脑根。它指向手机，不能解释 `.mfs` 的 `not authorized`。
3. 先做不依赖挂载/手解的插件库题。某一题连续两次没有新字段，写 UNKNOWN，做下一道独立题。禁止用一道 1 分的容器手解吃掉后面的插件库题。
4. `sqlite_query` 报 `not authorized`：语句是 `PRAGMA` 就改 `sqlite_master` + `SELECT * LIMIT 1`，禁止为此 `open_case`/`load_case`。只有 `SELECT` 失败才 load 计算机检材一次；成功后不要反复 load。

## 题面词 → 第一跳

| 题面词 | 第一跳 | 禁止 |
|---|---|---|
| BitLocker、恢复密钥 | `Win_BitlockerRecoveryKey.mfs` → `TBL_AF_BITLOCKER_PS_RECOVERYKEY` | 把密钥文件名或卷 GUID 的末几位当恢复密钥 |
| 远程连接、远程桌面、RDP | `Win_RemoteDesktopInfo.mfs` 成功连接表；没有再看 `Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx` | 题面没写向日葵/todesk/远控时，先翻 Sunlogin 日志或提交「成功接收到公网」 |
| 向日葵、sunlogin、todesk、远控软件 | 安装表 + 轮转日志；「成功接收到公网」后的对端 IP:port | 把中继、本机公网出口、相邻端口当答案 |
| VHD、虚拟磁盘、盘符 | 用户目录找 `*.vhd`；盘符来自挂载记录（注册表 `MountedDevices`、SetupAPI、分区诊断事件）或对副本 `Mount-Vhd -ReadOnly` | 手解 BAT/损坏 MBR。卷内扫到 JPEG/ZIP，或 boot 签名的 BPB 全零，都不能当成盘符或「这就是非加密分区」 |
| 该分区最后修改文件的 MD5 | 盘符或分区确定后再按修改时间取最新文件，在原始路径算 MD5 并转大写 | 分区未定时全盘哈希；FSData 的 md5 列为空时不要只查库 |
| VeraCrypt、加密容器、无后缀容器 | 先找模拟器备份（夜神 `.npbk` 等）里的微信/聊天，不要先上破解器 | 把容器当普通压缩包暴力；不要为看桌面去仿真开机 |
| 邮件、发件人 IP、附件 MD5 | 查 `Any_SingleMail.mfs`：`TBL_AF_SM_MAIL_DETAIL` 用 `IP_ADDRESS` 过滤发件 IP、按 `MAIL_SEND_TIME` 取最后一封；同一批查 `TBL_AF_SM_MAIL_ATTACH` 的 `FILE_MD5`（附件哈希在库里，不必落盘现算）。附件实体在 `<案件>\dev\<检材>\attachments\<uuid>\Attachment\`。`Win_Outlook` 只有 PST、`Any_ExchangeMail` 无表时不要解 PST | 用发件人显示名代替 IP；把 Win10Mail/Exchange 空库当成「没有邮件」 |
| torrent、Tor、onion | 先 Tor 的 `places.sqlite`（`...\TorBrowser\Data\Browser\profile.default\`），再 `Win_IDM.mfs` 下载历史，最后浏览器历史 | 只查 Chrome/Edge/IE；把下载文件名当答案 |
| 删除时间、回收站 | `Win_RecycleBin.mfs` 按文件名查；零命中再看该分区 `$Recycle.Bin\$I*` 的创建时间，按题面时区写出 | 插件表没有该文件名就判未删除；pending 已记零命中还去重复查同一张表；用 `$R` 内容文件的修改时间冒充删除时间 |
| GPS、经纬度、拍摄位置 | 先 `Any_ImageExifInfo`；邮件题的照片常不在该索引、经纬度列也可能为空。用 `Any_SingleMail` 锁定发件人与附件后，对 `<检材>\attachments\...` 的附件本体用 python PIL 读 EXIF GPS，度分秒换算后保留题面要求的小数位 | 只信一次换算、不保留原始度分秒；把本地唯一一张图的坐标当成邮件附件照片 |
| 登录失败次数、最后一次成功登录 | `Win_SystemLog.mfs` 的 `TBL_AF_WINLOG_LOG_SYSLOG` 查 `EVENT_ID='4625'`；该表 `ACCOUNT_NAME` 常为空，账号在 `POST_DATA`/`DESCRIPTION` XML 里，用 `POST_DATA LIKE '%<用户名>%'` 过滤。最后成功登录用 `EVENT_ID='4624'` 且 LogonType 2 确认，不要只信 pending 的假设或 `ACCOUNTLOGON` 的 START_TIME（无 END_TIME 的行不一定是失败） | 把其他用户的失败算进去；用最后一次开机代替最后一次成功登录；直接沿用 pending 里的旧时间 |

## 停止

- 手解 VHD、修复分区表、全量解码远控日志，都算高成本。两次无新字段就停。
- 盘符、删除时间、登录失败次数是主机痕迹，不在客户机内存里。不要改去开仿真看桌面。
- 模拟器备份和 VeraCrypt 容器用只读副本解析。不要把备份导入后的写操作落回原始检材。
