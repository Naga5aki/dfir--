# 本地取证模型升级方案（2026-11-11）

## 意图

本地做题丢分是走错路，不是解码不够快。同一台机器上，路线对的题在十几分钟内收口；路线错的题把预算耗在 VHD 手解、错误列、对 OLE 图片做 OCR 上。2026-11-10/11 的墙钟还掺进了两轮之间没立刻点「继续」的空档，不能用来验收。

本方案把已经写进技能、但压缩和长会话之后仍不被遵守的规则，变成每题进程的第一跳命令，然后在做过的 2024 数证杯卷上按占用时间复测。速度只做能减少空转回合的改动。

## 已测量的现状

运行栈：`D:\llm` 的 llama.cpp b11714，模型 `Qwen3.8-27B-IQ3-MIX`，`--spec-type draft-mtp --spec-draft-n-max 3`，`-c 65536`，KV q8_0，RTX 5080 Laptop 16GB。64K 窗口在 35–56K 上下文时 decode 掉到 11–14 token/s；32K 窗口下 30K 上下文测过 52.3 token/s。2026-11-07 用户要求改回 64K，本方案不改窗口。

做题入口有两套。验收用的是 `D:\ForensicsAgent\hermes\bin\dfir-solve.ps1`：一题一进程，基础 12 次工具迭代 / 480 秒，复杂题 16/600，失败后再给 6/240。交互长会话不是验收路径。2024 数证杯那几场走的是长会话，所以才会出现空档和一道题吃掉整卷。

占用时间口径（用户确认）：超过 5 分钟、且下一条是用户消息，算空档，从墙钟扣除。按 dfir-myos 会话库重算：

| 场次 | 墙钟 | 空档 | 占用 | 结果 |
|---|---:|---:|---:|---|
| 手机第二轮 `local-45ec02` 21:18–23:51 | 153 分 | 37 分 | 116 分 | 4/8，0 错答。OCR 实际约 60 分钟工具等待，不是两小时解码 |
| 计算机 `local-182284` 15:34–20:18 | 285 分 | 121 分 | 164 分 | 2/10，时间在 VHD 手解和反复 `load_case` |
| 计算机 `local-4226b9` | 97 分 | 55 分 | 42 分 | 前 18 分钟做对题 9、题 10 |

手机第一轮不在当前库里。那场 54 分钟里只有一次「继续」，两题是答错（区县、礼金），不是没跑完。礼金的 `SUM(DISTINCT)` 在第二轮已不再出现。

技能里已经有对的路由，模型仍会绕开：`ios-backup-ctf` 写明区县用 `ios_backup_probe.py districts`、图片先 `trailer`；`windows-computer-paper.md` 写明 VHD 不手解、4625 看 `POST_DATA`、邮件走 `Any_SingleMail`。第二轮加载了 iOS 技能，仍去解析 `ZLOCATIONDATA`，并对 `19.pic` 做 OCR。再往 SOUL 加段落不会修好这件事。

`dfir_router.py` 看到「手机取证」只注入 `mobile-ctf-pipeline`，不注入 `ios-backup-ctf`。计算机题只注入 `myos-results-analysis`，不指向 `windows-computer-paper.md` 的对应行。

金标曾经放在 `notes\` 里被模型读到并照抄。`eval_gold.py` 已把默认金标改到 `D:\ForensicsAgent\hermes\state\eval\`，且只覆盖 11–20 题。

## 目标

- 在 2024 数证杯手机卷、计算机卷上复测，用 `dfir-solve.ps1` 一题一进程。
- 错答为 0。UNKNOWN 不算错。
- 手机：题 1、4、5、6 不回退；题 3、7、8 做对。题 2 钥匙串无明文允许 UNKNOWN，不允许交一个编出来的密码。
- 计算机：题 1、2、9、10 不回退；题 6、7、8 做对。题 3 必须在自己的预算内结束：做对，或查过挂载记录后写 UNKNOWN。禁止手解 BAT/MBR。题 4、题 5 不预设对错，复测后按证据补路由，不在本方案里猜。
- 占用时间：单题不超过该题预算（基础 480 秒，复杂 600 秒）。整卷占用手机 ≤ 45 分钟、计算机 ≤ 60 分钟。这是本方案定的门槛，不是用户指定的数字。
- 单题注入后的提示停在 3 万 token 以内，这样 64K 窗口也不会掉进 11–14 token/s。

## 非目标

- 不上 DFlash2，不换显卡，不换模型，不把 `-c` 从 65536 改回 32768。
- 不把题解答案写进技能、SOUL、`notes\`、本文件。
- 不替换 `dfir-solve.ps1`，不重做 `docs\通用取证框架.md` 的通用 runner。
- 不在会话里写 keybag。题 2 无明文就是 UNKNOWN。
- 题面第 6 行粘着的「AI 视频条数」不进分母。指定题解没有这一问。
- 交互长会话不作为验收。用户仍可开长会话，但那不计入本方案的通过与否。

## 反目标

- 用墙钟或「感觉变快了」验收。
- 为了做对题，让模型读到金标。
- 再往 SOUL 堆规则，却不测新会话是否真的先跑第一跳。
- 一道容器题借走其他题的预算。一题一进程从结构上禁止这件事，实现时不要改回「十题一个会话」。

## 约束

- 实现改 `D:\ForensicsAgent\hermes\`。当前工作区是独立 worktree，里面的 profile 副本不是正在跑的那份，不要改工作区里的旧副本。
- 只改 `dfir-myos` 和 `dfir-max`。改之前复制到 `hermes\profiles\.backup-20261111-upgrade\`。
- 运行中的 gateway 不热加载技能。复测必须是新会话，不恢复 11-10/11-11 的长会话。
- 模型请求串行，单槽。`background_review` 保持关闭。压缩若发生，继续用 `local-plain`。
- 案件必须仍然能 `query_open_cases` 打开。打不开就停，不新建取证任务，不重新挂载去「修好」评测。
- 原始检材只读。探针只读 sqlite 和文件头。

## 做法

### 阶段 0：评测先于改动

1. 金标写成两个 JSON，放在 `D:\ForensicsAgent\hermes\state\eval\gold-2024szb-mobile.json` 和 `gold-2024szb-computer.json`。内容来自 2026-11-10/11 已对照过的题解和检材复核，由实现者填入。本文件、技能、SOUL、`notes\` 都不出现这些字符串。
2. 扩展 `eval_gold.py`，使 `--gold` 能评这两套卷。判定沿用现有规则：读 `pending-<题号>.md` 最后一条「答案：」行；UNKNOWN / 未取到 / 待确认 记为未答，不记为错；错答和未答分开计数。
3. 主用时取 `dfir-solve` 写入的 `_solve.log` 单题 elapsed。一题一进程时，这就是占用时间，不再扣用户空档。
4. 另写一个只读脚本，从 `C:\Users\TWK\AppData\Local\hermes\profiles\dfir-myos\state.db` 按「间隔 > 5 分钟且下一条 role=user」扣空档。只在有人仍用长会话时作对照，不作为通过条件。
5. 阶段 0 不改模型配置，不改技能。

### 阶段 1：第一跳变成命令，而不是另一段说明

不改 SOUL 正文。SOUL 里的纪律保持现状，避免提示更长。

改 `D:\ForensicsAgent\hermes\bin\dfir_router.py` 的 `local_skill` 和它拼进 `context` 的那一段：

- 题面是 iOS 备份（序列号、钥匙串、Platform/DeviceInfo、备份密码、区县、家庭地址、便签路由器）时，注入的技能是 `ios-backup-ctf`，不是 `mobile-ctf-pipeline`。
- 题面是 Windows 计算机卷（BitLocker、VHD、远程桌面、VeraCrypt、Tor、回收站、4625、邮件附件）时，注入「先读 `windows-computer-paper.md` 里与题面词同一行的第一跳和禁止列」。
- `context` 里加上该行的第一跳命令，要求本轮第一个工具调用就是它。命令文本从现有路由表抄，不新写查法。对应关系：

| 题面 | 第一个工具调用 | 返回后禁止 |
|---|---|---|
| 去过哪些区 | `ios_backup_probe.py districts <Photos.sqlite>` | 自行解析 `ZLOCATIONDATA`；全文 0 命中就换分支 |
| 家庭地址 | `sqlite_query` 当前案件 `GaoDeMap*.mfs` 的 `TBL_PR_GAODEMAP_GEO_ADDRESS_COLLECT` | 在文件系统里搜表名；改查通讯录 |
| 图片中的文档 | `ios_backup_probe.py trailer <图>` | 输出含 `D0CF11E0` 时对 PNG 表面 OCR |
| 记账金额 | 按交易 uuid 逐行相加。若探针没有求和子命令，实现者可以给 `ios_backup_probe.py` 加一个只读 `sum-by-uuid`，输入是账本路径和金额列 | `SUM(DISTINCT 金额)` |
| 钥匙串网站密码 | 只查 MYOS 是否已有明文凭据表 | 无明文就写 UNKNOWN 并停止，不写 keybag |
| BitLocker | `Win_BitlockerRecoveryKey.mfs` 的恢复密钥表 | 用文件名或卷 GUID 的末位 |
| 远程连接 | `Win_RemoteDesktopInfo` 成功连接表 | 题面没写向日葵时先翻向日葵日志 |
| VHD 盘符 | 挂载记录或只读 `Mount-Vhd` | 手解 BAT/MBR；两次无新字段就 UNKNOWN 并结束本进程 |
| 邮件 IP / 附件 MD5 / 邮件照片 GPS | `Any_SingleMail` 的 `IP_ADDRESS`、`FILE_MD5`；GPS 对附件本体用 PIL 读 EXIF | 只有 PST 就去解 PST；用 `Any_ImageExifInfo` 里另一张本地图 |
| 登录失败次数 | `Win_SystemLog` 的 4625，账号条件写在 `POST_DATA` | 用 `ACCOUNT_NAME` 为空判断「没有该用户」 |
| 回收站删除时间 | `Win_RecycleBin` 零命中再查 `$I` | 重复查同一张已零命中的表 |
| torrent / onion | Tor `places.sqlite`，然后 IDM，然后浏览器 | 只查 Chrome/Edge/IE |

`dfir-solve.ps1` 给单题 prompt 时带上路由器返回的第一跳。路由器没匹配到的题，prompt 保持现状，不发明第一跳。

`dfir-max` 使用同一份 `dfir_router.py` 和同一份技能文件。两份 profile 的技能若已分叉，以实现时 `dfir-myos` 的 `ios-backup-ctf` 和 `windows-computer-paper.md` 为准，把缺的行补到 `dfir-max`，不双向合并无关改动。

### 阶段 2：只在复测证明需要时才动速度旋钮

先跑阶段 3 的复测，再决定做不做下面两项。不预先改。

- 单题提示超过 3 万 token：削路由器注入的文本和技能正文，不改 `-c 65536`，不关 MTP。
- 占用时间主要耗在 thinking token 上（llama-server 日志里 reasoning 段明显长于工具等待）：用现成的 `local-plain` 对同一套题再跑一遍。正确数不降才把该域的默认从 `local-think` 改成 `local-plain`。只改被证明安全的域，不一次改掉两个 profile 的全部请求。

不做的速度项：DFlash2、加大 `--cache-ram`、`--backend-sampling`、把窗口改回 32K。前两者在 2026-10-30 的评测里已经回滚；窗口是用户改回去的。

### 阶段 3：复测

1. 路由器加字符串断言，不加载模型：iOS 区县题注入 `ios-backup-ctf` 和 `districts`；计算机 VHD 题注入停止句，且不注入向日葵；「手机取证」四个字单独出现时仍可注入 `mobile-ctf-pipeline`。现有 `benchmarks\mock` 的 59 项不能回退。
2. 真模型先手机 8 题，再计算机 10 题。每题新进程。不恢复旧会话。不把金标路径写进 prompt。
3. `eval_gold.py` 出表：正确、错答、未答、单题 elapsed、整卷占用、该题前 3 次工具名。`.mfs` 题的前 3 次里没有 `sqlite_query`，或图片题的第一次不是 `trailer`，记阶段 1 失败，即使答案碰巧对。
4. 错答或未答只改第一跳或停止条件。不把金标句子写进技能。改完只重跑失败题，外加一道已做对的邻题看回退。
5. 通过线见「目标」。没过就停在失败题的证据上，不扩大到换模型。

### 回滚

- 服务器配置本方案不改，无需回滚 llama.cpp。
- 技能和路由器回滚用 `.backup-20261111-upgrade`。
- `local-plain` 若在阶段 2 被设为默认，回滚就是把 profile `config.yaml` 的 `model.provider` 改回 `local-think`。备份那一次改动前的 yaml。

## 留给实现者

- 第一跳写进 prompt 的具体句式。
- 金标 JSON 的字段名，只要 `eval_gold.py` 读得了，且文件不在模型 cwd 和 `notes\` 下。
- `_solve.log` 的 elapsed 字段名，先读日志再解析，不要猜。
- `ios_backup_probe.py` 是否已有按 uuid 求和。没有再加，有就复用。
- 题 4、题 5 复测后的路由补丁。本方案不规定它们的查法。

## 本方案自己定的、可以改的决定

- 验收用 `dfir-solve` 单题 elapsed，不用长会话扣空档。扣空档脚本只作对照。
- 整卷门槛：手机 45 分钟，计算机 60 分钟。
- 计算机题 4、题 5 不设必对线。
- 阶段 2 的 plain 对照和削提示，以阶段 3 的测量为准，不预先做。
