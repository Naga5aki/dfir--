# Phase 4 Remediation-01 收尾批（批次 4-6，2026-09-05 实证）

承接 `phase4-remediation-01-answering.md`（批 2-3 首轮 25/29）。本文件记录批 4（纠错轮 → 29/29）、批 5（Memory 撤回）、批 6（验证器 v2 重建 20/20 + 12 探针全命中）。

## 批 4：纠错轮四项解码配方（读 generator 源码实证，全部与 truth 全等）

首轮答案冻结+评分完成后禁读期解除 → 读 generator 源码理解编码语义（禁读期内的穷举全部失败，读码一次命中）。

- **TR-13 MIDI note 承载**：`note = 0x40 + b % 0x60`，note-on 事件（status 0x90, vel=0x60 标记）每字符一事件。解码 `b = (note - 0x40) & 0x7F`，**模 0x60 歧义恢复**：`b < 0x20` 时 `b += 0x60`（回到可打印 ASCII）。msg2=P3-MIDI 是逐字节 `FF 01 01 <b>` 文本事件。评分器键名事故：answer 字段是 `msg1/msg2` 而比较器读 `msg` → 答案全对仍 FAIL——**比较器键必须对答案真实字段名**。
- **TR-16 PT2242**：TU=1 电平序列；帧=同步(1高,31低) + 20bit addr(MSB first) + 4bit data + 停止(1,3)；bit 脉宽 0=(1,3) 短高低长、1=(3,1)。帧长 132 电平（32+24×4+4），3frames 文件=132×3+帧间 [0]*2×2=400。解码=run 提取 → 找同步（run 对 (1,≤2) 后 (0,≥20)）→ 每 bit 对按 `l>=2h→0 / h>=2l→1` 判决 → addr20+data4。truth 的 bits=24 不含停止位（task 口径冻结）。
- **TR-17 URB 帧**：pcap 包数据=**`"URB"+0x43+urb_id(1)+direction(1)+dev(1)+ep(2B <H>)+payload`**（不是 "URBC"！URBC 是早期轮 generator 的旧约定）。HID 报告 usage=payload[2]（报告 8B: mod/res/usage/…）；dir=0x80=IN 计入、0x00=OUT 干扰拒（n_out_reject）。solver 找 "URBC" 字符串致帧识别空——**帧签名以 generator 现场代码为准，不沿用上轮记忆**。
- **TR-26 SNMPv3 USM 命中组合**：engineID=用户名（`transfer_user`）前**最早**的 `04 0c` 段（secpar 内 engine；authParam 的 04 0c 在 user 后、scoped 里还有第三个 04 0c）；**m2 重建必须保留 OCTET STRING tag**：`m2 = msg[:ap+2] + b"\x00"*12 + msg[ap+14:]`（ap=04 tag 位置；漏 tag 曾致 HMAC 恒不中）。Ku=SHA1(pw 扩展 1,048,576B)→Kul=SHA1(Ku‖engine‖Ku)→HMAC-SHA1(Kul,m2)[:12]==auth。

纠错轮落盘：`remediation-results-rem01.json`（first_round 原样 + root_cause + remediation + verdict="复现…"）；**首轮证据保留披露**——首轮答案文件被纠错重跑同路径覆盖，首轮哈希仍存档于 `rem01-first-run-frozen.json`（25/29 版），评分文件被重算覆盖，均须在纠错记录如实披露（round-1 判定 25/29 + FAIL 清单另有 checkpoint 存档）。

## 批 5：Memory 撤回与 pre-Phase4 恢复（教师 C2）

- **备份选源陷阱**：教师指令后的\"门禁快照备份\"（remediation-01/snapshots/memory-backup/）是 **post-Phase4 状态**（含 4C 写入版与新知识文件）——真 pre-Phase4 基线在 **4C 应用前备份**（`phase4/memory-backup/`，playbooks 36,076/60c50588…、training 21,580/aa4c4847…、index 7,917/da76aed4…）。先核对备份哈希与阶段链记录一致再用。
- 流程：post-Phase4 7 文件移入 `remediation-01/post-phase4-memory-archive/`（+archive-manifest.json 大小/SHA）→ staging 重建（memory-restore-staging/）核对基线 5/5 → 正式区恢复 → **磁盘回读 5/5**（memory-rollback-record.json）→ 正式区无 misc-knowledge-summary.md。重新晋级必须等闭卷+迁移门禁全过（闭卷 Pending ⇒ 晋级阻塞）。

## 批 6：增强验证器 v2（F01-F20）与探针

20 项检查映射教师 §三.4 十二项要求（详见 SKILL.md 主文清单），关键实现点：
- **F04 Memory pre-Phase4 恢复态**：5 文件**完整 64 位 SHA**（非前缀）+ misc/misc-knowledge-summary.md 不存在断言。
- **F05 闭卷作废/Pending**：issue-register 含\"旧题作废\"、checkpoint 含 Remediation Required——不要写自创的 split/否定逻辑（曾误判）。
- **F06-F08 冻结现场复算**：逐行解析 sha256 清单 `^([0-9a-f]{64})  (.+?) \((\d+) B\)$` 并核对 SHA+大小双项。
- **F15 泄漏扫描范围**：**pack/answers/observation-log 天然含解码产物（TRANSFER4_ 明文载体）不能当泄漏**；扫描对象=正式 Memory + restore-staging + remediation 记录区（排除归档目录 post-phase4-memory-archive/round1-transfer-archive/memory-backup/snapshots）。SOURCE 完整哈希出现在 counts/issue-register=元信息记录，从禁入词移除。
- F17 计数实测：从运行记录文件读（counts-rem01.json 由实际工具使用维护），非硬编码。
- finally 快照：异常路径也执行（坏 json 探针 rc=1 + `FINALLY_SNAPSHOT MATCH` 实证）。

### 探针目标命中铁律（v1 首轮 12 探针全中招的教训）
- **outdir 放 --root 副本内=假通过**：rc=3 入口拒绝先触发，探针\"rc≠0 达标\"但目标检查从未跑到 ⇒ output-dir 必须放副本外（Temp 独立目录）。
- **mutate 必须使目标检查 FAIL 且失败项含目标**：p10 泄漏注入 memory 文件 → F04 先 FAIL（哈希变）而 F15 不触发 ⇒ 注入**不触发其它检查的文件**（remediation 记录区 json）使 F15 独中；p11 outdir 探针在 mutate 回调内自断言 rc==3（不走通用 run 包装）；p12 异常探针=写坏 JSON 使验证器中途异常 → 断言 rc≠0 且 stdout 含 FINALLY_SNAPSHOT MATCH。
- 每探针记录 rc/hit/fails 落盘（probe-results-rem01.json）；**clean 副本 rc=0 是探针套件有效的必要条件**（v1 曾因 fh 过期 clean rc=1——重跑前重新 mkroot）。

## 本批陷阱速查
- Python <3.12 f-string 表达式内禁反斜杠（`b"\x00"` in f-string ⇒ SyntaxError 且**批脚本静默零输出**，grep FAIL=0 是假象——核对答案文件数与 py_compile）。
- 评分器比较键必须对 answer 真实字段名；周期 XOR 密钥整倍重复先规约再比。
- 多文件循环内嵌 obs() 步序断言崩 ⇒ step2 观察收集到循环外一次发出。
- 验证器修完（F21 增强等）⇒ fh 同步 ⇒ 重新 mkroot clean 复核，避免旧副本 fh 过期误报。
- 探针 mutate 目标键已存在=空转（覆盖已有处分键 len 不变）⇒ 用新增键/越界值保证目标检查必 FAIL。
