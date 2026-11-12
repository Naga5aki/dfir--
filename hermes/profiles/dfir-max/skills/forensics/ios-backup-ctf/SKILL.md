---
name: ios-backup-ctf
description: Use when the phone evidence is an iPhone, iOS, or iTunes backup (序列号, 备份密码, keychain-backup.plist, Platform/DeviceInfo, Containers/Data/Application) or a mobile contest item about 钥匙串, 记账金额, 去过的区, 家庭地址, 路由器密码, or a picture with an appended document.
---

# iOS 备份赛题

iOS 备份不是 Android。`data\data\<pkg>`、`myos_mount.json`、别的赛题的 `device_map` 都不是本案根。

## 开局

1. `notes\device_map.myos.summary.txt` 的赛名必须和题面一致。不一致就丢掉，`query_open_cases` 按赛名锁定 caseId，再 `query_device_mount_path`。不要找 `myos_mount.json`。
2. 有 `Platform/DeviceInfo` 或 `Containers/Data/Application` 就是 iOS。已装 App 在这个目录的 bundle 名里，不在 `data\data`。
3. `.mfs` 只走 `sqlite_query`。python 报 `file is not a database` 就停，不要重试。
4. 读到一个值立刻写 `notes\pending-<题号>.md`（答案 / 证据 / 已排除 / 下一轮），再做下一题。压缩之后先读 pending，禁止重放同一组 `ls`/`find`。

两问粘在一行时按问号拆开。`【答案格式】` 里的示例不是答案。

## 直查

| 题型 | 第一跳 | 禁止 |
|---|---|---|
| 序列号 | `Platform/DeviceInfo/Manifest.plist` 的 SerialNumber，或 `query_device_info` | 用别的案件摘要 |
| 包名 | Info.plist / `TBL_APPDATA_MANAGER`。记账类从枚举到的名称认 | 猜 `jizhang` |
| 记账金额 | 明文账本。分类名精确匹配，按交易 uuid 去重，逐行相加 | `SUM(DISTINCT 金额)` |
| 网站密码 | 先查 MYOS 有没有凭据表。`v_Data` 里没有明文域名就是密文 | 会话里写 keybag/PBKDF2 |
| 家里路由器 | 所有包名含 `note` 的便签，取含“路由器密码”的原句 | 从 Wi‑Fi 列表挑 SSID |
| 去过哪些区 | `python -X utf8 D:\ForensicsAgent\hermes\bin\ios_backup_probe.py districts <Photos.sqlite>`。区县在 `ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA`，不是 `ZASSET.ZLOCATIONDATA` | 把 ZLOCATIONDATA 解析失败当成“没有区县”；全文搜 0 命中就放弃 |
| 最新家庭地址 | `sqlite_query` 案件 `MApps/GaoDeMap*.mfs` 的 `TBL_PR_GAODEMAP_GEO_ADDRESS_COLLECT`，`REMARK='家'`，丢掉 `DELETE_STATUS=1`，按 `CREATE_TIME` 取最新。缺市名再补 | 在备份文件系统里搜这个表名；搜不到就改查通讯录 |
| 图片里的文档 | 先 `ios_backup_probe.py trailer <图>`。输出 `D0CF11E0` 就从 `carve_offset` 切开，口令是同一条聊天里的短文本 | 对 PNG 表面跑 OCR |
| 生成条数 | 先枚举 bundle。没有独立 App 就只查一次已装短视频 App 的任务表 | 把格式示例当答案 |

## 金额

和账户余额对照后，`money` 是分就除以 100。去重键是 uuid，不是金额。两笔相同金额都要加。`SUM(DISTINCT money)` 会吃掉第二笔。pending 写下每一行；各行之和必须等于提交值，不等就重加，不要交。

## 地点和地址

`ZASSET.ZLOCATIONDATA` 是坐标二进制，`plistlib` 会报 Invalid file。这不表示没有区县。区县在另一张表：

```
python -X utf8 D:\ForensicsAgent\hermes\bin\ios_backup_probe.py districts "<Root>/private/var/mobile/Media/PhotoData/Photos.sqlite"
```

输出里的「区」才是选项。经度只分桶。全文搜索 青秀/历城 0 命中不能否定这个 blob。没有该区就不选。联系人 position、地图搜索词、路线缓存都不是到访。

家庭地址不在备份文件名里。`.mfs` 不是明文，文件系统搜不到 `GEO_ADDRESS_COLLECT` 是正常的。只做一次：

`sqlite_query`，dbPath = 案件目录 `MApps/GaoDeMap{GUID}.mfs`，SQL = `SELECT CREATE_TIME, DELETE_STATUS, COMPANY_ADDRESS, EVENT_PLACE, REMARK FROM TBL_PR_GAODEMAP_GEO_ADDRESS_COLLECT WHERE REMARK='家'`。

丢掉 `DELETE_STATUS=1`，按时间取最新。字段没有市名就补该区所属的市。

## 图片尾部

SOUL 里的“图片直接 OCR”不适用于微信 `Img/*.pic`。先跑：

```
python -X utf8 D:\ForensicsAgent\hermes\bin\ios_backup_probe.py trailer "<图>"
```

出现 `do_not_ocr_png_surface` 就按 `carve_offset` 切出 OLE，用同一条聊天里的短文本当口令。不要装 tesseract，不要重跑 OCR。

### 聊天图片题的通法

凡是「聊天里发来的图片/文件里有什么」的题，按同一条链走，不要猜目录：

1. 在 MYOS 的 `*.mfs` 里定位消息：`TBL_PR_WEIXIN_IM_*` 找文本命中和图片消息（`MEDIA_TYPE=02`、`md5=`）。文本消息会给出上下文和疑似口令（短字母数字，如 `mm20241105`）。
2. 用 md5/图片序号在案件挂载根下找到实体：`Containers/Data/Application/<微信容器>/Documents/<hash>/Img/<会话hash>/<序号>.pic`。找不到就用 `bash` 通配 `*/Img/*/<序号>.pic` 一次，不要逐层 `ls`。
3. 跑 `trailer`。出现 `D0CF11E0` 时，用同一会话的聊天库和表名跑 `docprice`：

```
python -X utf8 D:\ForensicsAgent\hermes\bin\ios_backup_probe.py docprice "<图>" <品类关键词> "<message_3.sqlite>" "Chat_<会话hash>"
```

`docprice` 会打印 `PASSWORD`、`ROW`、`PRICE`。价格在输出的 `PRICE` 行，单位为元/克。没有 `D0CF11E0` 才考虑 OCR。
4. 找不到实体图时，先在 `message_3.sqlite` 的 `Chat_*` 表核对序号，再回到第 2 步；不要对 `TBL_PR_WEIXIN_IM_*` 的图片字段直接做 OCR。

## 钥匙串

`Platform.mfs` 的 Wi‑Fi 表和系统账号表不是网站密码。plist 解不开就写 `答案：UNKNOWN`，证据写 plist 路径，停止。不要实现解密。

## 红旗 — 停，回到上表

- 正在写 PBKDF2 / keybag
- SQL 里出现 `SUM(DISTINCT`
- 把 `ZLOCATIONDATA` 解析失败当成没有区县
- 文件系统搜不到 `GEO_ADDRESS_COLLECT` 就改查通讯录
- 对 `do_not_ocr_png_surface` 的图跑 OCR
- 把题面要求的密码打成 [REDACTED]
- 压缩后重放同一组命令
