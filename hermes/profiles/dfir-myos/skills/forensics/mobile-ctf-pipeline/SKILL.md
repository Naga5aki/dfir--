---
name: mobile-ctf-pipeline
description: 手机取证（Android）流水线：索引→定位→取数→收口；含微信 key、图片二维码、VeraCrypt 链.
---

# 手机取证流水线（本地模型版）

目标：**用最少的轮次拿到原始字段**。每一步都优先"读现成索引"，而不是让模型自己 ls / find。

## 2025 FIC 手机检材2 实战补丁（先读）

本赛题实测：49 次 API 调用、6 次压缩、约 59 分钟；纯 decode 39.17 t/s（≥30K 上下文），主调用端到端 21.6 t/s，任务级 10.3 t/s。瓶颈在流程（上下文/压缩/重复探索），不是模型。先按下面顺序走：

1. **便签先枚举所有便签/备忘录 App，不要只开 `com.miui.notes`。** 本检材 PC 密码在 `com.bijoysingh.yang\databases\note-database`，秘钥环在 `com.miui.notes\databases\note.db` 的 `data` 副表；`com.lazy.note` 也有 6 个库。每题一次 dump `note` + `data`/`note_data`，完整滚动/JSON；PC 密码与秘钥环是两个值，不能混。
2. **微信 key 先试默认串，再试真实 IMEI。** 微信 8.0.42–8.0.57 常见：`MD5("1234567890ABCDEF" + UIN)[:7]`；失败再试真实 IMEI+UIN。禁用 MEID。**必须用 SQLCipher/DB Browser 打开 EnMicroMsg.db 验证**；`KeyInfo.bin`（17B 密文）/`mmkv_private` 不是首选路线，连续 2 次失败就换公式。
3. **Q8 key 失败不阻塞 Q9。** 聊天图片附件是明文：去 `MicroMsg\<md5>\attachment`、`data\media\0` 找两张图片；拼接/增强 → `qr_scan.py`/stegstove → 手机号 → RAR 密码。密码可能是 `+1` 区号后的号码；带/不带区号都试，以能解压为准。不要把 Q9 挂在“解密微信库”上。
4. **`1.png` 低对比度先增强再 OCR**（PIL/ImageMagick/随波逐流）；VC 容器 MD5 对原始容器文件算；姓名/金额在 VC 挂载后的欠条里。
5. **倒数日 Realm 不是只搜字符串。** `default.realm` 的标题与日期数组按对象顺序映射；本赛题 5 组标题/日期，取对应项，按题面格式写；无法映射就 OCR App 截图交叉验证。
6. **OCR 出完整暗号句就收口。** 本赛题暗号是图片里的 13 字歌词句，不是歌名；OCR 已读出完整句子就提交，不要因“不确定”写 UNKNOWN。答案必须是原始字段/图片文字，题面格式示例不是答案。
7. **一题一进程，先走关键链。** Q6/Q7 → Q8 key → Q9 RAR → Q10–Q13 VC 是主链；先把主链打通，再做便签/日期支线。本赛题 49 次调用/6 次压缩/59 分钟；单题 scoped run（Q2 243s、Q7 81s）明显更快。

## 答案验证门禁（2025-10-31 盲测强制）

写 `答案：` 前逐条过；任何一条没过，只能写低置信度或 `答案：UNKNOWN`，不能写“已解决/中高”。

1. **时间类**：Realm 的 `dueDate` 是 int64 毫秒，必须按 `Asia/Shanghai` 换算。若结果比 WP/原图早一天，先怀疑 UTC 偏移；用 `default.realm` 里的 ASCII 日期串或截图交叉验证。盲测教训：把 +08:00 的日期写成了 UTC 的前一天。
2. **微信 key**：WeChat DB key 只取 MD5 前 **7 位**；算出 14/32 位必须截断到 7 位。必须用 SQLCipher/DB Browser 打开 `EnMicroMsg.db` 验证；打不开就写 `UNKNOWN`/低置信度，不能把 14 位候选当答案。盲测教训：已算对 MD5 前缀却提交了 14 位。
3. **置信度/状态**：没有做决定性验证（打开库、完整 realm 映射、OCR 原文、哈希复算、时区核对）的题，置信度只能写“低”或 `答案：UNKNOWN`，状态不能写“已解决”；写清还差哪一步。

## 阶段 0：索引（不花模型轮次）

`myos_appmap.py` 已把检材扫成地图，MYOS 也已完成手机分析，产物：

- `notes\device_map.myos.summary.txt` —— MYOS 已完成分析索引：已解析 App、`appMfsPath`、数据项数、`sqliteQueryHints`。**优先读；微信/已解析 App 题直接用 sqlite_query。**
- `notes\device_map.summary.txt` —— 一屏摘要：第三方包、每个包库数、`files` 下关键子目录与条目数、含聊天库的包、媒体目录计数、工程/草稿目录实测值。MYOS 未解析的 notes/realm/图片从这里取 ROOT 与线索。
- `notes\device_map.json` —— 需要细节时按包名取条目（库文件名、表名、行数、mmkv 列表、chat_dbs 路径）。

不要 `ls data/data`、不要 `find *.db`、不要挨个 `sqlite_master` 枚举。地图已经回答了"哪里有数据"。

**隔离纪律**：`notes` 目录内只读 `notes\device_map.*`、`notes\tool-map.md`、本题 `evidence-q<题号>.txt`、`pending-<题号>.md`；检材原始数据的只读访问不受此限。禁止读 `notes` 下其它文件、`_solve-*.log`、`cases\archive`、任何 gold/eval/参考答案文件。题面逐字来自本题 `notes\questions-<范围>.txt` 的 `题号|题干` 行，按题号取，不要猜题意；范围必须与当前案件一致。

## 阶段 1：定位（1–2 轮）

按题型直接落到唯一路径。表里没写的题，先在 map 的 summary 里找包，再查 `device_map.json` 对应包的 `databases[].tables`。

| 题型 | 直查路径 | 关键判据 |
|---|---|---|
| 设备标识（Android ID / IMEI） | 设备信息面板 / `ssaid.xml` 的 `settings` | 16 位十六进制 |
| WiFi 最后连接时间 | `data\misc\apexdata\com.android.wifi\WifiConfigStore.xml` 或 `data\misc\wifi\WifiConfigStore.xml` | `SSID` + `LastConnectedTime`=毫秒时间戳，按东八区换算 |
| IM/直播聊天条数、发送失败条数 | `<pkg>\files\<uid>_<hex>\msg_0.db` → `message(sid,status,sender,content)` | `status=3` 失败、`2` 正常；`sid`=对方 user_id |
| 昵称 → user_id | 同目录 `im.db` 的 `userinfo` | 不要全局搜昵称 |
| 搜索关键词 | `<pkg>\files\mmkv\dbb_ugc_editor_home_history_biz` 的 `_search_history_info_key` | `dbb_search_tab_key` 只是页签，不是关键词；先 `strings` 看内容再下结论 |
| 文件加密后后缀 / 解密后缀 | 解密输出文件的实际扩展名（`tmp` / `mp4` …） | 以文件系统实测为准，不看工具默认值 |
| 网站/API 端口 | 聊天文本 URL 或浏览器 `History` | 取 `:port` |
| App 名称（包名→中文名） | `apklist.mfs`（走 MCP `sqlite_query`） | 0 字节时改看 `Platform.mfs` 或桌面清单 |
| 加固/加密工具 | 第三方包清单里 `com.aijiami.cn` 类 | 用户目录只有 cache 也算命中 |
| 加密算法/模式 | 复制 APK 到工作区 → `powershell -File D:\ForensicsAgent\hermes\bin\ensure-jadx.ps1 -Apk <APK>` → MCP 反编译 | 8650 不通时用上面的脚本（WMI 拉起可常驻）；兜底 `python D:\ForensicsAgent\hermes\bin\dex_strings.py <apk>` |
| 剪映/抖音工程目录名 | `files\newdrafts`（UUID 目录才是工程） | `draft` 只有 placeholder PNG、`tmp` 是缓存；不猜目录名 |
| 视频生成条数/模型名 | `com.bytedance.dreamina\databases\dreamina.db` → `aigc_data.data_json` | `model_info.model_name` |
| 图片里的金额/中签结果 | 图库文件 → `hermes\bin\ocr.ps1` | 只取数字 |
| 口述密码 | 音频转写/试听 + Keepass 库 | 注意大小写与 `@` |
| 手机号/登录名 | 短信库→通话库→通讯录→App `mmkv` 账号→浏览器表单 | 通讯录/短信为空别扫系统黄页（客服号噪声）；微信/支付宝是加密库 |
| 视频里的链接/画面文字 | `qr_scan.py "<视频>" 1 200`；无码再 `video_frames.py "<视频>" <目录> 20 12` + `ocr.ps1 -Path <目录>` | 先确认视频与题材相关，无关立刻换源 |
| 便签里的 PC 密码/秘钥环/接头暗号 | 枚举所有便签/备忘录 App：`com.miui.notes\databases\note.db`（note + data 副表）、`com.bijoysingh.yang\databases\note-database`、`com.lazy.note`、memo APK；一次完整 dump | 答案常在副表；PC 密码与秘钥环是两个值；不要只开 MIUI 便签 |
| 倒数日/最重要的日子 | `com.clover.daysmatter\files\default.realm` 按对象映射标题↔日期（不只搜字符串）+ `data\media\0` 截图 `ocr.ps1` | databases 只有埋点；5 组标题/日期常按顺序对应；两条都做完才算排除 |
| 微信库加密密钥 | 先 `md5("1234567890ABCDEF" + UIN)[:7]`（微信 8.0.42–8.0.57），失败再 `md5(IMEI + UIN)[:7]`（uin 取 authUin/auth_info_key_prefs.xml） | 禁用 meid；必须用 SQLCipher/DB Browser 打开 EnMicroMsg.db 验证；KeyInfo.bin/mmkv 不是首选 |

## 阶段 2：取数（1–2 轮）

- 明文库：**一条 `dbq.py` 命令出结果**，不要写多行 `python -c`（Windows 引号嵌套必错，实测每错一次烧掉 1–2 轮）：

  ```
  python D:\ForensicsAgent\hermes\bin\dbq.py "<root>\data\data\<pkg>\files\<uid>_<hex>\msg_0.db" --tables
  python D:\ForensicsAgent\hermes\bin\dbq.py "<root>\data\data\<pkg>\...\msg_0.db" "SELECT COUNT(*) FROM message WHERE sid='1731375' AND status=3"
  ```

  `<root>` 占位符由脚本自动展开；结果首行列名，第二行起是值；加 `--json` 出结构化。
- 明文库也可用 `terminal` + `python -c` 单行只读 URI `file:///C:/...?mode=ro`，但优先 `dbq.py`。
- `.mfs` 加密库：只走 MCP `sqlite_query`；`python sqlite3` / `dbq.py` 必报 `not a database`。
- MCP 返回 `{"error":"not authorized"}` → **第 2 次失败立刻换 `dbq.py`**，不要第 3 次重试。
- 大结果先 `write` 到 `notes\` 再分段读，避免 2000 字符截断。

## 阶段 3：收口（1 轮，强制）

写入 `notes\pending-<题号>.md`：

```
题<号>（一句话题意）
答案：<严格符合题面【答案格式】的最终值>
证据：<root 相对路径 + 表名 + 字段值>
已排除：<走过的错误分支>
下一轮：完成 / <下一步>
```

- `答案：` 行只能有一个最终值；不确定写 `答案：UNKNOWN`，不许编造，**不许把题面示例值当答案**。
- **预算前 1/3 内（默认约第 3 次工具迭代；预算更短时至少第 1 次后）先写一次占位（答案 UNKNOWN），之后每拿到关键字段就覆盖更新**；覆盖前必须先 `read_file` 读当前文件再 `write_file`，否则工具会以"未见过该文件当前内容"拒绝覆盖（实测丢过 2 题）。
- 时间：原始时间戳 + 换算结果 + 时区。哈希：原始路径 + 算法 + 截取位数。数量：两个来源。

## 预算纪律

- 预算由外层 `dfir-solve.ps1` 的 `--max-turns` / `--run-budget` 传入；**不要自行写死 12/480 或 6 次迭代**。`--max-turns` 是工具调用迭代上限（日志中的 “12 tool calls”），不是对话轮数。基础题 12/480，复杂题 16/600；首次失败且仍有具体下一步只再给 6/240，撞硬墙/工具阻塞/已列出已排除路径不再重试。
- 是否继续看可观察信号：出现新相关证据、缩小候选、排除具体假设、修复工具错误 → 可以继续；连续 2 次工具迭代没有新增证据/没有缩小候选，或同一工具/查询连续 2 次失败且没有新修复路径 → 立即收口，写 `答案：UNKNOWN` + 证据定位 + 已排除 + 下一条具体命令。剩余预算不足以完成下一项高成本操作时先落盘。
- 一题一进程：不要在一个会话里连做多题，会长上下文压缩并烧光预算（实测 10 题 2 次压缩、0 收口）。

## 验收

`hermes\bin\eval_gold.py` 对照当前题号范围的 `D:\ForensicsAgent\hermes\state\eval\gold-<范围>.json`（金标在模型工作目录之外，禁止读取），输出 `正确/总题` + 单题用时。
历史 11-20 题集的验收门槛（正确 ≥8/10、单题 ≤13 分钟、压缩 0 次）只适用于该题集；当前 2025fic Q1-8 没有当前金标时逐题人工核对，不能套用旧范围的 gold。

## 跨检材链式题

手机题解不开的答案，答案支点常在别的检材或另一个文件里。按下面的链式路径推进，链上每一环都要落盘再走下一环：

| 题面形态 | 链式路径 | 断链判据 |
|---|---|---|
| 压缩包 / 文档密码 | 微信聊天图片（可能两张需拼接）→ `qr_scan.py`/stegstove 扫码 → 手机号 → 密码（可能带 `+1` 区号；带/不带都试） | **Q8 key 失败不阻塞本链：聊天图片附件是明文**；单张扫码 0 命中先拼图再扫，仍 0 命中改 OCR |
| 容器密码（VeraCrypt） | 图片低对比度 → 增强 → `ocr.ps1`；容器 MD5 对原始文件算、只读挂载 | 不增强就 OCR 大概率读错字符 |
| 真实文件类型 | magic bytes 判定 → 复制副本改后缀 → 再解一层 | important.docx 实为 zip、内层 xml 实为 JPEG(FFD8FF) |
| 远程控制记录 | `sunlogin*` 日志（含 `.log.N` 轮转）按题面时间定位 → 同段公网 IP:端口 | 只看最新日志会漏轮转文件 |
| 音频内容 | 有 ASR 走转写；无 ASR 判分段藏头（每段首字连读） | 分段异常本身就是线索，别当噪声 |
| 自定义顶级域（.foren6） | `dig NS` 拿 NS 地址 → 指向该 NS 查 A/MX/TXT（HNS 区块链） | 普通 dig 无 answer 是 DNS 依赖未满足，不是命令错 |

