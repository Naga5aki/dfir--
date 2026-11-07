---
name: android-app-forensics
description: Use when Android userdata/手机检材需按 App 定位数据库、MMKV、缓存、聊天记录或图片证据；含 MYOS 解析库入口与手机取证答题校验规则.
---

# Android App Forensics

AI 主导的 Android 手机检材分析。目标：**先走 MYOS 解析结果，再回落文件系统**，把"猜 App / 猜包名 / 猜表"的轮次压到 0。

## 结论收口

下结论前读 `references/evidence-record.md`。解题答案不写等级词。没有当次回执的句子写“未取到”，不要写成不存在。

## 铁律（违反即浪费 2–6 轮）

1. **先解析库，后文件系统。** `data\MApps.mfs`、`data\apklist.mfs`、`data\MApps\<App>{GUID}.mfs` 是 MYOS 已解析好的结果，优先查它们。
2. **一切名字必须来自枚举。** 包名、App 名、表名、库文件名都要来自 `apklist.mfs` / `MApps.mfs` / 目录枚举，**禁止凭记忆写**（本次把 DeepSeek 猜成 `com.bytedance.dreamina`）。
3. **`.mfs` 只能走 MCP `sqlite_query`。** 用 `python sqlite3` 打开必报 `file is not a database`（已实测），不要重试。sqlite_query 的 `dbPath` 必须来自当前案件的 mount/overview/sqliteQueryHints/device_map；遇 `not authorized` 先 query_open_cases → query_materials → query_*_overview 核对 caseId 与 mount root，**不要原样重试同一路径**；明文库用 `dbq.py`。
4. **图片不要 `read_file`。** 返回 `is_image: false, content: ""`，直接调 `ocr.ps1`。
5. **大返回先落盘。** 超过 2000 字符的 JSON（如结果总览）先 `write` 到 `notes\`，再分段读；一次性灌上下文会被截断在关键字段之前。
6. **子库缺失立刻回落原始明文库。** MYOS 只解析了部分 App（本案 17 个子库覆盖 DeepSeek/JianYing/HuanYou/SouGouInput/JiaoGuan12123/MiCloud/XiaoMiMarket，**不含即梦、抖音**）。若 `MApps` 下找不到目标 App 的子库，直接走 `<root>\data\data\<pkg>\databases\*.db`，用 `python sqlite3` 只读打开（`file:...?mode=ro`，明文可直接查）。**不要为了找子库把 17 个库全枚举一遍**——那会烧光预算还得不到答案（本次 Q9 就是这么失败的）。
7. **题面【答案格式】里的示例值不是答案。** `【答案格式：seedance1.5pro】` 只是格式示范；照抄会得到一个格式完全正确、内容完全错误的答案（本次 Q9 输出 `seedance1.5pro`，实际是 `seedance1.0fast`）。任何结论必须有库里读出的原始字段支撑，没有就写"未取到"。 
8. **先读数据源地图，不要枚举。** 本题 `notes\device_map.summary.txt`（当前案件根由 dfir-solve/dfir-run 设置）由 `hermes\bin\myos_appmap.py` 扫出：第三方包、每个明文库的表与行数、含聊天库的包、媒体目录计数、工程/草稿目录实测值（59 包 96 库，0.9 秒）。开局读它；需要细节再读 `device_map.json` 对应条目。**不要 `ls data/data` 或 `find *.db`**。
9. **每题一个收口文件。** 写 `notes\pending-<题号>.md`（题号/答案/证据/已排除/下一轮），字段名固定为 `答案：`。十题合成一个文件会导致无法逐题判定、重试与评测。
10. **明文库只用 `dbq.py` 取数。** `python D:\ForensicsAgent\hermes\bin\dbq.py "<root>\...\x.db" --tables` / `... "SELECT ..."`（只读、自动展开 `<root>`、首行列名）。不要写多行 `python -c`——Windows 引号嵌套必错，本次实测每错一次浪费 1–2 轮。`execute_code` 可能因审批或引号问题失败；失败一次就改用 terminal / `dbq.py`，不要连续重试。
11. **答题隔离：答案只能来自检材或数据源地图。** `notes` 目录内只读 `notes\device_map.*`、`notes\tool-map.md`、本题 `evidence-q<题号>.txt` 与 `pending-<题号>.md`；检材原始数据的只读访问不受此限。**禁止**读 `notes` 下其它文件、`_solve-*.log`、`cases\archive`、以及任何 gold/eval/参考答案文件。历史结论照抄会让评测失效、错误不可复现；题面逐字取自 `notes\questions-<范围>.txt`，按题号取行，不要靠猜题意。

## 原始文件系统的 root 在哪（不要 ls 到处找）

`<root>` 的权威来源：本题 `notes\device_map.summary.txt` 顶部的 `ROOT = ...`（当前案件根由 dfir-solve/dfir-run 设置）；summary 缺失/过期时才读 `D:\ForensicsAgent\hermes\state\myos_mount.json` 的 `rootPath`/`root`。路径形如 `C:\osmap\<GUID>_<时间戳>\Root`，也可能是其下的 `\userdata`，**以 summary 实测为准**。

- summary 和 mount 都不存在 → 先跑 `python D:\ForensicsAgent\hermes\bin\myos_mount.py mount`，再读它们。
- **不要**去 `D:\MYOS\Case\...\dev\userdata.tar\` 下面找 `data\data`、`files\`、`attachments\`：检材目录只有 MYOS 的 `.mfs` 与索引库，原始文件系统只在 `C:\osmap` 挂载点。
- 拿到 root 后：App 私有数据 = `<rootPath>\data\data\<pkg>\`。层级随检材而异：拼路径前先 `ls <root>/data` 确认——若直接列出 `com.*` 包目录，则 App 私有数据是 `<root>\data\<pkg>\`（少一层，tar userdata 直挂的镜像即如此）；`data\system` 等目录也可能不存在（Android 10+ 系统分区在镜像外），找不到就换 `quick_search_files` 定位，不要假设固定布局。

## 开局顺序（按需，不要机械跑）

```text
0. 先读本题 notes\device_map.myos.summary.txt（MYOS 已完成分析索引）：有 appMfsPath 的微信/已解析 App 题直接用 sqlite_query 查；MYOS 未解析的 notes/realm/图片再读 device_map.summary.txt 的 ROOT 与线索
1. MYOS 索引缺失/过期或需核对 caseId/mount：query_open_cases → query_materials → query_phone_forensics_results_overview；总览很大，不要整份读，找 sqliteQueryHints/mfsStats 即可
2. device_map.summary 缺失/过期：读 D:\ForensicsAgent\hermes\state\myos_mount.json 的 rootPath；不存在 → python D:\ForensicsAgent\hermes\bin\myos_mount.py mount
3. 只有包名↔App 名缺失时才 sqlite_query(MApps.mfs / apklist.mfs)；不要为开局完整性全量枚举
4. 设备级信息优先 props / settings_global.xml，必要时 query_current_node_data
```

## 目录入口

| 目标 | 路径 |
|---|---|
| App 私有数据 | `<root>\data\data\<pkg>\` |
| 数据库 | `...\databases\*.db`（含 `-wal` / `-journal`，先读 wal） |
| 键值 | `...\shared_prefs\*.xml`、`...\files\mmkv\*.mmkv` |
| 媒体 | `<root>\data\media\0\`（DCIM / Movies / Download / Pictures） |
| 无线网络 | `data\misc\apexdata\com.android.wifi\WifiConfigStore.xml` |
| 设备账户 | `data\system\users\0\settings_ssaid.xml`（每 App key，不是设备 Android ID） |
| 输入法 | `...\com.sohu.inputmethod.sogou\databases\` |
| MYOS 解析子库 | `<MYOS案件>\dev\<检材>\data\MApps\<App>{GUID}.mfs` |

## 存储形态判定树

```text
MApps 下有该 App 子库？          → sqlite_query 查 <App>{GUID}.mfs
MApps 下无该 App 子库？          → 立刻回落 <root>\data\data\<pkg>\databases\*.db（明文，python sqlite3 只读可开）
有 databases/*.db 明文？        → sqlite3 直查
有 files/mmkv/*.mmkv？         → MMKV（不是 XML），strings / hexdump 找 key（简记事邮箱即此类）
只有 shared_prefs/*.xml？      → SharedPreferences
只有 -wal 没有主库内容？        → 先解析 wal
文本全局搜零命中？              → 三选一：图片(OCR) / 加密库(decrypt_partition) / App 子库
```

## 题型 → 直查路径（高频 12 类；长尾见 `references\question-routing.md`）

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 最后连接某 SSID 的时间 | `WifiConfigStore.xml` 的 `LastConnectedTime` | 毫秒时间戳，必须脚本换算成 `Asia/Shanghai` |
| 某 App 的登录邮箱/账号 | App 的 `mmkv` 或 `shared_prefs` | 简记事在 `files/mmkv/mmkv.default` |
| 某个文件名 / 提示词文件的 MD5 | `data\media\0\` 或全局文件名搜索 | **在原始路径算哈希**，不要对副本算 |
| AI 生成内容的条数 | `com.bytedance.dreamina\databases\dreamina.db` 的 `aigc_data` + `data\media\0\` 文件枚举 | 即梦未被子库解析，走原始库；本案例 3 条 |
| 某个 `history_record_id` 的模型名 | 同上库同表，`data_json` 里的 `model_info.model_name` | 本案例 `Seedance 1.0 Fast` → `seedance1.0fast` |
| App 中文名 / 引流软件 | `apklist.mfs`（包名↔App 名） | 一条 SQL，不要靠猜；**先确认非 0 字节**，空文件时走 ls data/data + Platform.mfs |
| 剪辑工程数（剪映） | `files\newdrafts\` 下列目录（UUID 命名者为用户工程） | 剪映子库只有 BROWSE_MULTIMEDIA / BROWSE_SEARCH / BROWSE_ACCOUNT 三表，**无工程表**；`files\draft` 只有 placeholder PNG（非工程）；`AlbumToVideoId` 类自动目录不计 |
| Android ID / 设备信息 | 设备信息面板 / `query_current_node_data` | 不要逐条读 ssaid.xml |
| 中签截图 / 余额 / 认购金额 | 图库 `DCIM_*.jpg` → `ocr.ps1` | 取数字，不逐字抄；中文会插空格 |
| 聊天记录条数 / 发送失败条数 | `<pkg>\files\<uid>_<hex>\msg_0.db` → `message` 表；`status=3` 失败、`2` 正常；`sid`=对方 user_id | 昵称→user_id 先查同目录 `im.db` 的 `userinfo`；`databases\elp_msg.db` 只有 `msg(workId,expireTime)`，**不是聊天内容** |
| 售卖 API / 网站端口 | 聊天文本里的 URL 或浏览器历史 | 取 URL 的 `:port` |
| 直播软件搜索关键词 | `<pkg>\files\mmkv\dbb_ugc_editor_home_history_biz` 的 `_search_history_info_key`（JSON，字段 `name`） | **`dbb_search_tab_key` 是搜索页签（综合/团购/商品…），不是关键词**，本检材实测关键词只在上面的 history 文件 |

长尾题型（加固逆向 / 剪映工程 / 音频 / 微信 / 媒体 OCR / 便签日程）→ 读 `references\question-routing.md` 的对应段落，不要整篇读。

## 反模式（本次踩过，别重复）

- ✗ 开局就 `ls data/data | grep -v com.android` 看包名 → 烧 token 且不知道 App 名（apklist.mfs 为空时例外：那是唯一包名清单，见开局步骤 3 的例外）
- ✗ `cat` 3000 字符 XML 全文 → 用 `grep` 只取命中行
- ✗ 同一个关键字换 3 种拼法继续全局搜 → 2 次零命中就换分支
- ✗ Windows 下 python sqlite3 用单斜线 URI `file:C:/...?mode=ro` 打开原生 .db → 直接报 `unable to open database file`；URI 要 `file:///C:/...` 三斜线，或把 .db 拷到临时目录再开（不要对证据路径拿可写句柄）
- ✗ 只查一个 App 就回答数量类题 → 至少两个来源
- ✗ 结论写"待确认"就交付 → 时间戳/哈希必须当场算清写死
- ✗ 把 `MApps` 下 17 个子库挨个 `sqlite_master` 枚举找目标 App → 目标不在就永远找不到，烧光预算（Q9 实测 36 次调用后仍空手）
- ✗ 把 `databases\elp_msg.db` 当聊天库 → 它只有 `msg(workId,expireTime)`；真正的消息在 `files\<uid>_<hex>\msg_0.db`（Q11 因此多花 10+ 轮）
- ✗ 工程目录名靠猜（`draft` / `drafts` / `newdrafts` / `tmp` 都试一遍）→ 先读 device_map 的实测行
- ✗ `sqlite_query` 返回 `{"error":"not authorized"}` 还连续重试 PRAGMA 变体 → `.mfs` 上 `PRAGMA table_info` 可能被禁（Platform.mfs 实测），第 2 次失败改走 `SELECT name FROM sqlite_master` + `SELECT * FROM <表> LIMIT 1`（看行键取列名）；`python3 sqlite3` 直连只用于明文库 `.db`，对 `.mfs` 必报 `file is not a database`
- ✗ 十题写进同一个 `pending-1-10.md` → 预算耗尽后无法逐题重试（本次 11–20 题 0 收口）
- ✗ 把"用户数据为空"当成"不是目标应用" → 加固/加密工具往往只有 `cache` 与 `code_cache`，包名本身就是答案
- ✗ 看到 mmkv 文件名像就不再验证内容 → 本检材 `dbb_search_tab_key` 存的是页签、`dbb_ugc_editor_home_history_biz` 里才是搜索历史；**先 strings 看内容，键名只当线索**
- ✗ 对 `.encrypted` 密文直接扫码/OCR → 全是乱码；必须先按上面的解密行解出明文再抽帧（实测 87 MB 素材解密后才可播）
- ✗ 解密素材扫码 0 命中还继续换步长/帧数重扫 → 说明该素材根本不含二维码，换素材或换题链，别在一处磨
- ✗ "databases 目录里没有业务表"就判定 App 无数据 → Days Matter 真数据在 `files\default.realm`，聊天类可能在 `files\<uid>_<hex>\`
- ✗ 只查便签主表/只开 MIUI 便签就交付 → PC 密码可能在 `com.bijoysingh.yang` 的 `note-database`，秘钥环在 `com.miui.notes` 的 `note.db` data 副表；枚举所有便签/备忘录 App
- ✗ 推微信 key 时用 meid 或只试一枚 IMEI → 先试默认串 `1234567890ABCDEF`+UIN，再试两枚 IMEI；禁用 meid；必须打开库验证
- ✗ 把"打开 note.db / default.realm"排进"下一轮" → 预算耗尽后这两个库从未被打开，题目直接归零；要么本轮打开，要么先落盘 UNKNOWN + 下一步命令
- ✗ 把 Q8 微信 key 当成 Q9 的前置 → Q9 的聊天图片在明文附件里，key 解不开也能做；先拼图/扫码
- ✗ 在 KeyInfo.bin/mmkv_private 上连续尝试 → 先走标准 MD5 公式并打开库验证，2 次失败换图片链
- ✗ OCR 出完整暗号句还写 UNKNOWN → 直接提交原始文字，不要空着
- ✗ 只取 Realm 字符串池不做标题↔日期映射 → 按对象顺序映射，或 OCR 截图交叉验证

## 答案验证门禁（2025-10-31 盲测强制）

写 `答案：` 前逐条过；任何一条没过，只能写低置信度或 `答案：UNKNOWN`，不能写“已解决/中高”。

1. **时间类**：Realm 的 `dueDate` 是 int64 毫秒，必须按 `Asia/Shanghai` 换算。若结果比 WP/原图早一天，先怀疑 UTC 偏移；用 `default.realm` 里的 ASCII 日期串或截图交叉验证。盲测教训：把 +08:00 的日期写成了 UTC 的前一天。
2. **微信 key**：WeChat DB key 只取 MD5 前 **7 位**；算出 14/32 位必须截断到 7 位。必须用 SQLCipher/DB Browser 打开 `EnMicroMsg.db` 验证；打不开就写 `UNKNOWN`/低置信度，不能把 14 位候选当答案。盲测教训：已算对 MD5 前缀却提交了 14 位。
3. **置信度/状态**：没有做决定性验证（打开库、完整 realm 映射、OCR 原文、哈希复算、时区核对）的题，置信度只能写“低”或 `答案：UNKNOWN`，状态不能写“已解决”；写清还差哪一步。

## 2025 FIC 手机检材2 实战补丁

- **便签/备忘录枚举多个 App**：`com.miui.notes`（note.db 的 note + data 副表）、`com.bijoysingh.yang`（note-database）、`com.lazy.note`（6 个库）、memo APK。PC 密码与秘钥环是两个值；只查 MIUI 便签会答错。
- **微信 key 顺序**：先 `MD5("1234567890ABCDEF" + UIN)[:7]`（8.0.42–8.0.57），再真实 IMEI；禁用 MEID；必须打开 EnMicroMsg.db 验证；`KeyInfo.bin`（17B）/`mmkv_private` 不是首选。
- **Q8 key 失败不阻塞 Q9**：聊天图片附件是明文，去 `MicroMsg\<md5>\attachment`/`data\media\0` 找两张图，拼接/增强 → 二维码 → 手机号 → RAR 密码；带/不带 `+1` 都试。
- **低对比度 `1.png` 先增强再 OCR**；VC 容器 MD5 对原始文件算；姓名/金额在 VC 挂载后的欠条。
- **Realm 日期**：按对象顺序映射标题↔日期，不只 `strings`；截图 OCR 交叉验证。
- **OCR 出完整暗号句就提交**；不要留 UNKNOWN。

## 收口校验（提交前逐条过）

1. 时间类：原始值 + 换算结果 + 时区，三者齐全。
2. 哈希类：原始路径 + 算法 + 截取规则，可复现。
3. 数量类：两个来源，数量一致或解释差异。
4. 名称类：来自枚举，有包名/表名支撑。
5. 答案格式：严格符合题面【答案格式】，大小写/位数/连接符不漏；**但绝不用格式里的示例值当答案**。
6. 落地：写入 `notes\pending-<题号>.md`，`答案：` 行只有一个最终值；不确定写 `答案：UNKNOWN`。没有这个文件等于本题未作答。

## 相关文件

- 数据源地图（开局先读）：本题 `notes\device_map.summary.txt`（当前案件根）；全量 `device_map.json`
- 题面：本题 `notes\questions-<范围>.txt`（`题号|题干` 一行一题）；题号范围必须与当次案件一致，不能拿旧题集代替
- 金标与评测：`D:\ForensicsAgent\hermes\state\eval\gold-<范围>.json`、`hermes\bin\eval_gold.py`（金标**不在** notes 下，禁止读取）；没有当前范围金标时就人工核对，不能套用旧范围金标
- 工具真名与易错点：`D:\forensics\cases\notes\tool-map.md`
- 本案数据源地图：`D:\forensics\cases\notes\datasources.md`
- 已排除路径：`D:\forensics\cases\notes\rejects.md`
- OCR：`D:\ForensicsAgent\hermes\bin\ocr.ps1 -Path <文件|目录> [-Out <txt>]`
- 索引脚本：`D:\ForensicsAgent\hermes\bin\myos_appmap.py`
