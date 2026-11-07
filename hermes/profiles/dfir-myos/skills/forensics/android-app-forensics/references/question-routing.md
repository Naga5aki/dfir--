# 题型 → 直查路径（长尾）

主文件 `SKILL.md` 只保留高频 12 类；本文件收长尾题型。**按题面关键词只读对应段落，不要整篇读**（每次多读 4 KB ≈ 多 1 秒 prefill，且挤占上下文）。

## 加固与逆向

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 文件加密 / 加固工具包名 | 第三方包清单里 `com.aijiami.cn` 这类应用 | 用户数据为空也成立；算法走 jadx |
| 加密算法 / 模式 | 先把 APK 复制到工作区 → `powershell -File D:\ForensicsAgent\hermes\bin\ensure-jadx.ps1 -Apk <APK>` → 8650 通后用 MCP 反编译 `EncryptionUtils` | 不要用 `Start-Process` 起 jadx（GUI 子进程随终端回收，实测 30s 消失），脚本内部走 WMI；也不要直接打开检材里的 APK（jadx 会写缓存）。兜底：`python D:\ForensicsAgent\hermes\bin\dex_strings.py <apk>` 扫 dex 常量 |

## 工程与目录

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 剪映 / 抖音工程目录名 | `files\newdrafts`（UUID 目录）才是工程本体 | `draft` 是占位图目录，`tmp` 是缓存；以实测字段为准，不要照抄目录名 |

## 音频

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 口述密码 | 音频转写 / 试听 + Keepass 线索（详见下方"口述密码（音频）"行） | 注意大小写与 `@` |
| 口述密码（音频） | `<root>\data\media\0\Recordings\*.wav` 存在即说明密码靠听；本机无 ASR 引擎 | 没有转写能力就写 `答案：UNKNOWN`，不要猜；可在"下一轮"里写明"需人工听写/需接 whisper" |

## 微信

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 微信聊天记录（MYOS 已解析） | `MApps\Wechat{GUID}.mfs`：消息主表 `TBL_PR_WEIXIN_IM_CONTACTMSG`（`CONTENT` / `ORIGINAL_CONTENT`），账号表 `TBL_PR_WEIXIN_IM_ACCOUNT`（`ACCOUNT_ID` 即 UIN、wxid、昵称） | 多个 Wechat{GUID} 子库时逐个查账号表确认哪个含目标账号；`PRAGMA table_info` 不可用，列名靠 `SELECT * LIMIT 1` |
| 微信数据库文件名 / 加密密钥 / 账号 UIN / device_name | 详见 `references\wechat.md`（UIN 的 `TBL_PR_APP_AUTHINFO.authUin` 交叉验证、keyfile 缺失时的候选位置、`persist.sys.device_name` 在 lspd props.txt） | 未解析的微信走文件系统；`*.mfs` 只能走 `sqlite_query`，python sqlite3 打不开 |
| 微信库加密密钥（无 keyfile） | 详见 `references\wechat.md` 的"密钥推导"节：`md5(uin+imei)` 取前 7 位小写十六进制 | 多枚 IMEI 逐个试，**不要用 meid**；key 必须能打开库或与库内明文表对照成功后才写死 |

## 媒体与 OCR

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 二维码 / 下载链接 | `python D:\ForensicsAgent\hermes\bin\qr_scan.py "<视频或图片>" [步长秒=0.5] [最多帧=200]` | 本机无 ffmpeg/zbar，脚本用 cv2 抽帧解码；无二维码时说明链接是画面文字，抽帧后 `ocr.ps1` 读文字。顺序不能反（先解密再抽帧） |
| 手机号 / 登录名 | 顺序：短信 `mmssms.db` → 通话 `calllog.db` → 联系人 `contacts2.db` → 直播/业务 App 的 `files\mmkv\config_biz` → 剪映 `files\home_feed_cache\key_*.json` 的 `web_uid` → 浏览器表单 `Web Data` | `web_uid` 常是「手机号 + 4 位随机数」（实测 `1354235344600631` → 前 11 位即手机号）；不要假定 SIM 号 = 登录号；微信/支付宝库为加密库，明文中查不到不代表没有；通讯录/短信为空时不要去扫系统黄页库（`yellow_pages.dat` 全是客服号，纯噪声） |
| 视频里的链接 / 画面文字 | `python D:\ForensicsAgent\hermes\bin\qr_scan.py "<视频>" 1 200`；无码再 `python D:\ForensicsAgent\hermes\bin\video_frames.py "<视频>" <输出目录> 20 12` + `ocr.ps1 -Path <输出目录>` | 先判断视频是不是题材相关（本检材 `Movies\直播素材\待剪辑\算力宣传视频.mp4` 实为 Stable Diffusion 演示，与矿机无关）；无关就换别的视频或换来源，别在 OCR 上耗预算。**链接类题常见链式路径：聊天记录提到 → 聊天里的宣传视频 →（视频若加密则先解密）→ 扫码/OCR**；三处都没有就写 `答案：UNKNOWN` 并注"需联网/人工复核"，不要反复调帧率 |
| 加密素材（`.encrypted` / `.tmp.encrypted`）解密 | `python D:\ForensicsAgent\hermes\bin\aijiami_decrypt.py "<密文>" "<输出路径>" "<密码>"`；先 `--probe` 只解前 64 字节验密码（输出 `mp4=True` 即对） | 算法：AES-256-CBC/PKCS7，key=SHA-256(password)，IV=`juhetianji123456`；解密后按真实内容判断类型（无后缀也先按视频试）。**顺序：解密 → 抽帧/扫码/OCR**，不要对密文直接 `qr_scan` |

## 便签与日程

| 题面关键词 | 直接查 | 备注 |
|---|---|---|
| 便签里的 PC 密码 / 秘钥环 / 接头暗号 | 系统便签 `com.miui.notes\databases\note.db`（及 `todo.db`）→ `--tables` 后**每张表** `SELECT * LIMIT 50`，含 `data` / `note_data` 这类副表 | 答案常在 `data` 副表而**不在** `note` 主表，自动解析界面也不展示；三问同源时整表 dump 一次 grep，别逐题重开库；壳类记事 App 只有 SDK/WebView 文件可直接排除 |
| 接头暗号（图片型线索） | 便签 JSON 里 `format:IMAGE` 的 `text` 就是文件名（如 `ub690t1mq9kelnah.png`）→ 在 `<pkg>\files\`（含 attachments）按文件名定位 → 复制只读副本 → `ocr.ps1 -Path <png>` | 图片不 `read_file`；找不到实体时先按文件名全局搜索，再看 capabilities 是否被系统压缩改名 |
| 一生中最重要的日子 / 倒数日 | `com.clover.daysmatter\files\default.realm`（字节解码 + 中文正则）**并** `data\media\0` 下截图 OCR | `databases` 里只有埋点表；Realm 无解析器不算排除，截图里常直接印着日期（本赛题 2026-02-26 走截图更快） |
