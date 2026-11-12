# 计算机取证总框架（关键词驱动）

目标：把「题目 → 关键词 → 数据源 → 原始字段 → 答案」变成可重复的短路径；本地模型每轮 10-85s，必须先用关键词缩小范围，再打开文件/库。

## 1. 五步循环

1. **拆题**：从题面抽 5 类关键词。
   - 实体：人名、手机号、邮箱、域名、IP、账号、文件名、哈希、版本号。
   - 工件：开机/关机、USB、浏览器、微信、远控、日志、文档、音频、便签、哈希。
   - 时间：题面时间戳、日期、时区；先换算成 epoch/毫秒。
   - 格式：单选/多选/简答；选项原文；逐字匹配要求。
   - 证据号：检材三/电脑/手机；确认挂载根（不要用 myos_mount.json 的手机根）。
2. **选层**：按速度分四层，先上后下。
   - L1 MYOS 插件库（`IntegrateForensics/*.mfs`）：结构化、最快。
   - L2 原始文件系统文本/配置/日志：`/home/<user>`、`文档/桌面/下载`、`/var/log`、`.config`。
   - L3 二进制/加密容器：VMDK、Chrome `Login Data`、keyring、ZIP/DOCX、图片、音频。
   - L4 全盘/大目录关键词：最后手段，必须有 `timeout`、`-m`、目录/类型/时间限制。
3. **搜关键词**：先精确值（哈希、手机号、域名、题面原词），再同义词/英文/包名/字段名；每次记录「范围 + 命中文件/表 + 字段」。
4. **验证**：至少一个原始字段或两个独立来源；选项题先看选项是否与证据一致；时间戳换算时区；区分观察/推断。
5. **收口**：写 pending（答案/证据/已排除/下一轮）；解题阶段只提交答案，**不写 writeup**；用户明确要求计分/复盘时再补。

## 2. 题型 → 关键词 → 数据源矩阵

本表是 2025FIC Linux 例题，不是当前试卷。题号含义以题面原文为准。Windows 题（BitLocker、VHD、远程连接、VeraCrypt、Tor、回收站、登录失败）先看 [windows-computer-paper.md](./windows-computer-paper.md)。

| 题型 | 高信号关键词 | L1 插件库/表 | L2/L3 原始位置 | 关键字段/命令 |
|---|---|---|---|---|
| 最后开机/关机 | 开机、关机、boot、shutdown、wtmp、BOOT_TIME、最后 | `Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN` | `/var/log/wtmp`、`boot.log`、syslog `Booting paravirtualized kernel` | START_TIME/END_TIME；wtmp 384B，u32 tv_sec@340；选项冲突时最多交叉一次 |
| USB | USB、设备、ThinkPlus、VID、PID、最近使用 | `Linux_UsbInfo` / `Win_USB` | `/var/log/syslog`、`/var/log/kern.log`、`~/.local/share/recently-used.xbel` | 设备名/序列号/首次/最后时间 |
| 远控软件 | 向日葵、sunlogin、todesk、raylink、远控、公网、IP、端口 | `Linux_InstallSoftWare` | `/var/log/sunlogin/`、`/opt`、`/usr/bin`、桌面 `.desktop` | PACKAGE_NAME/SOFTWARE_VERSION；`sunlogin_service.log*` |
| 向日葵会话 | 2025-04-10 11:04:29、express login、success、公网 | — | `Partition2/var/log/sunlogin/sunlogin_service.log*`、`desktop.agent.log`、`shell.log` | 先按时间戳定位 `.log.N`；`成功接收到公网` 后 IP:port 优先提交 |
| 浏览器密码 | 域名、dgy02、Chrome、password、钥匙环、keyring | `Any_Chrome.TBL_AF_CHROME_WEB_LOGINDATA`、`Any_ChromiumBrowser` | `~/.config/google-chrome/Default/Login Data`、`Local State`、`~/.local/share/keyrings/*.keyring` | origin_url/username_value/password_value；v10/v11 + Safe Storage；用 `chrome_login_decrypt.py`（GNOME keyring→PBKDF2→AES-CBC） |
| 微信版本/账号 | 微信、wechat、版本、包名、UIN | `Linux_InstallSoftWare`、`Win_WeChat` | `~/.xwechat/`、`文档/xwechat_files*`、`/var/lib/dpkg/status` | PACKAGE_NAME=`wechat-beta`、SOFTWARE_VERSION |
| 文档/助记词 | MD5、文件名、助记词、wallet、important.docx | `FSData.mfs` `TBL_FS_ENTRY_*`（md5 可能为空）、`Any_OfficeMetaInfo` | `图片/`、`文档/`、`桌面/`、`下载/` | 先按文件名/大小缩小；对候选现算 `md5sum`；magic bytes |
| 哈希→文件名 | 32 位十六进制、MD5、文件 | `FSData.mfs` | 用户目录最近文档/图片 | `md5sum <候选>`；FSData md5 为空时不要只查库 |
| 嵌套 VM | 我的测试机、虚拟机、VMware、vmdk、便签、音频 | — | `文档/我的测试机/*.vmdk`、`.vmx`、`mksSandbox*` | `myos_nested_vm.py --dry-run` 后 `--yes`（add_image_material→load_case→query_device_mount_path）；VM 内便签/浏览器/音频 |
| 便签隐藏图 | 国庆、便签、note、base64、PNG | — | VM 内便签库/附件 | `content` 列 `data:image/...;base64,...`→PNG→OCR |
| 音频内容 | 音频、MP3、转写、毕业、姓氏、酒店、密码、分段 | — | VM 用户目录 `音频/`、`文档/` | ASR；异常静音分段取每段首字；记录段数 |
| 手机号/账号 | 备用机、号码、1[3-9]\d{9}、MSISDN、邮箱 | 联系人/短信/微信/便签库 | 便签正文、聊天记录、文档 | 正则 `1[3-9][0-9]{9}`；去空格/连字符 |
| 域名/IP | 域名、DNS、IP、端口、URL、foren6 | 浏览器历史、网络配置 | Chrome History、`/etc/hosts`、`/etc/resolv.conf` | `dig`/`nslookup`；HNS 自定义 TLD 先查 NS |

## 3. 关键词检索命令（Windows/Git Bash）

### 3.0 一键关键词计划/有界搜索

```bash
python -I D:\ForensicsAgent\hermes\bin\computer_keyword_search.py \
  --question "<逐字题面>" --notes D:\forensics\cases\notes \
  --root "C:/osmap/<id>/Root" --execute --timeout 60 --max-hits 30
```

输出：哈希/手机号/域名/版本/中文实体/英文实体、命中的数据源插件、候选目录、SQL 模板、grep 命令、有界全文命中（文件名/内容）。先看命中再打开文件，不要直接全盘 grep。

### 3.1 SQLite 插件库

```sql
-- 先看表，再搜文本列；不要一上来 SELECT *
SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';
-- 单表关键词（大小写不敏感）
SELECT * FROM <表> WHERE lower(<文本列>) LIKE '%关键词%' LIMIT 20;
-- 多表联合（表名/列名来自 sqlite_master，不要猜）
SELECT '<表1>' AS src, * FROM <表1> WHERE lower(<列>) LIKE '%kw%'
UNION ALL SELECT '<表2>', * FROM <表2> WHERE lower(<列>) LIKE '%kw%' LIMIT 50;
```

`.mfs` 只能走 MYOS `sqlite_query`；明文库可用 `dbq.py`/`sqlite3` 只读。`PRAGMA table_info` 被拒时改走 `sqlite_master` + `SELECT * LIMIT 1` 看列名。

### 3.2 文本/日志/配置

```bash
# 目标目录内按类型搜，命中即停；不要全盘
timeout 60 grep -r -a -l -I -m1 \
  --include='*.txt' --include='*.log' --include='*.json' --include='*.xml' \
  --include='*.ini' --include='*.conf' --include='*.desktop' \
  '关键词1\|关键词2' "<目录>" 2>/dev/null | head -20

# 文件名
find "<目录>" -maxdepth 4 -iname '*sunlogin*' -o -iname '*important*' -o -iname '*vmdk'

# 按时间/大小缩小
find "<目录>" -type f -mtime -30 -size -50M -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort | tail -40
```

### 3.3 二进制/容器

```bash
# 二进制内关键词 + 偏移
timeout 120 grep -a -b -m5 '关键词' <file>
strings -a -n 6 <file> | grep -i -E 'sunlogin|dgy02|tcgg|wechat|password' | head -20

# DOCX/ZIP：先看 magic
xxd -l 16 important.docx          # 504B0304 = ZIP；FFD8FFE0 = JPEG
7z l important.docx; 7z x important.docx -o<work>

# base64 图片
grep -a -o 'data:image/[^;]*;base64,[A-Za-z0-9+/=]*' <db> | head -1
```

### 3.4 哈希/时间

```bash
md5sum "<候选文件>"                 # FSData md5 为空时对候选现算
date -d @<epoch> '+%F %T %z'        # 秒；毫秒先 /1000
```

## 4. 搜索纪律（本地模型）

- **先精确、后模糊**：哈希/手机号/域名/题面原词一次命中；零命中再同义词/英文/包名。
- **两次零命中换分支**：图片 OCR / 加密库 / 嵌套 VM / 文档解析；不要换拼法重试。手解 VHD/BAT/分区表两次无新字段，同样换题，不要继续修偏移。
- **题面压过例题**：本表和压缩摘要里的「题3/下一题」与题面冲突时，以题面为准，并重读题面文件。
- **有界**：每次 `timeout`、`-m`、`--include`、`maxdepth`；禁止对 13GB 文档树/12MB syslog 全量读。
- **命中即停**：拿到字段就写 pending，不要继续逛；连续 2 次无新证据收口。
- **候选排序**：题面要求的字段 > 日志原句 > 同义候选；同一题最多试 2 个候选，不耗光平台次数。
- **选项止损**：四源一致但选项不含真实值时，最多交叉一次；按选项一致值或问用户一次。
- **解题阶段不写 writeup**：`submit_answer` 返回 correct 后直接继续下一题；除非用户明确要求计分/复盘，不补 writeup。

## 5. 典型链式题

1. 手机便签/聊天 → 钥匙环/密码 → 电脑 Chrome → 域名密码。
2. 图片/二维码 → 手机号 → RAR 密码 → VC 容器 → 文档/图片。
3. 电脑镜像 → 嵌套 VMDK → 便签/浏览器/音频 → 备用机/密码/音频答案。
4. 日志时间戳 → 轮转文件 `.log.N` → 会话窗口 IP:port → 选项/简答。
5. 哈希 → 候选文件现算 → 容器套娃（docx→zip→xml→JPEG）→ 助记词。
