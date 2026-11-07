---
name: phase-gated-docx-learning
description: Use when running SecurityLab 方案A gated docx learning phases.
version: 1.0.0
author: hermes-curator
license: CC-BY-4.0
metadata:
  hermes:
    tags: [security, docx, knowledge-cards, memory-mapping, verification, ctf]
    related_skills: [ctf-misc-analysis, digital-forensics]
---

# 阶段门禁式 DOCX 知识学习流水线（SecurityLab 方案A）

## When to Use
- 触发：训练者/教师下发方案A指令、阶段指令、差分重基线指令、定向纠错与全量复核指令、独立闭卷题包（Pack zip 附件）（附件路径带 Context Warning 属正常——登记后按指令只读执行）。
- 场景：对大型 .docx 学习材料做盘点提取、逐批知识卡与 Memory 映射、冲突审计、纠错轮、后续微型实验与闭卷测试；出现"门禁/锚点/漂移/纠错报告/知识卡"字样时本技能生效。
- 不适用：普通单次 CTF 解题或文件分析（走 ctf-misc / ctf-misc-analysis）。

把一份大型 .docx 学习材料按教师审核门禁推进：阶段1 盘点/保真提取 → 阶段2 知识卡+Memory 映射+冲突审计 →（纠错轮）→ 阶段3 微型实验 → 阶段4 闭卷/迁移测试。每阶段完成必须停止并交报告，等训练者/教师新指令；教师中途下发的"定向纠错与复核指令"按 remediation 流程处理。

## 铁律（每轮必做）
1. 源文件只读（`rb`/`zipfile`）；`~$*.docx` 锁文件存在 ⇒ Source Still Open，不执行任何修改。
2. 开始门禁：锁文件不存在 + SOURCE_DOCX 双 SHA-256（两次之间完成一次完整结构读取）+ 全部锚点核对（源/提取物/报告/项目 Memory 哈希，按指令给的清单逐项）。任一 FAIL ⇒ 停止并报告精确漂移；**禁止**重建源、重提取、覆盖 Memory、改锚点来通过检查。
3. 结论分级 Observation / Inference / Alternatives / Conclusion / Next Validation；无实证不下直判；不选边。
4. 计数逐轮申报：下载/联网/安装/升级/实验/测试/项目 Memory 写入/全局 Memory 写入/P 编号改动。
5. 写入范围只限指令"本轮允许修改"清单；清单外文件（源、阶段1文件、data、images、Memory）只读。
6. 报告硬性项：真实命令+真实输出（不写"已运行"）；哈希完整 64 位小写（禁 8 位前缀）；文件大小/派生物以现场实算为准；编号全局唯一。

## 批次执行模式（阶段2 等大批量建卡）
1. 由 coverage/headings 生成批次行段图（每批 8 个 H1 左右），按行段读提取稿。
2. 每批立即落盘四件套：知识卡（17 字段模板）追加、claim 主张段、memory-map 映射段、coverage H1/H2/T 状态更新；批次检查点文件同步。
3. 上下文不足 ⇒ 停在本批结束后（批边界），更新检查点文件，绝不跨批写半张卡、绝不因卡多跳主题。
4. 每批完成做一次磁盘回读核验（哈希/末条记录/重复/结构），不凭"刚写过"宣称存在。
5. 全批完成后跑只读终验脚本：数量 + 结构 + 锚点 + Memory 哈希全查，任一 FAIL 不得写 Completed。

## 高风险陷阱（每一条都来自真实事故，详见 references/execution-playbook.md）
- **编号体系先验 0 基还是 1 基**：本类文档表格编号从 T-0 起（T-0..T-171）；H1/H2 逐级编号与全局序不同源。先读文件确认，勿假设。
- **P 编号空洞 = 空段落**：extracted 展示稿只标非空段，P 存在性校验必须以 `data/paras.json` 全量编号（连续全集）为权威，否则范围定位符误报 FAIL。
- **Markdown 表格内 `||`**（如 `SC||Blob`）会撑破列结构 ⇒ 改写为 `concat(SC, Blob)`；审计须逐表头逐行列数，禁止"让脚本忽略多余列"。
- **报告内嵌自身 SHA-256 永不收敛**（写入即改变文件）⇒ 不内嵌，注明终值以交付消息为准；或先冻结再在外层给哈希。
- **ID 重编号**：只允许在指令要求拆分/重排时做；必须保存旧 ID→新 ID 映射 JSON，并把正文交叉引用按映射**迭代替换到收敛**（链式 A→B→C），终检 0 残留；禁止静默重编号。
- **replace 未命中仍报 OK**：所有批量替换必须断言旧串存在/输出替换计数；"print OK" 不是成功证据（曾致 map 两批段静默丢失）。
- **分类判定须全文读取参考材料**：抽样/索引读取会导致系统性误判（一次 9 处分类错误）；guide 卡"点名级"（出现考点名/工具名）= Verified Extension 的基础；标题相同≠Exact Duplicate（需同字段细节）；主题相邻≠Verified Extension（需共享字段/位序/步骤）。
- **Conflict Register**：分 Active Conflicts 与 Historical Candidates Reclassified（Extension/Example/Tool-Gap/Document-Specific boundary 四去向）；Active 数量必须与 memory-map 的 Conflict 卡数、claim 的 Conflict-Pending 状态数三方一致；Active=0 时就写 0，保留历史候选审计轨迹。
- **claim 主张行**：主状态必须单一且来自允许状态集（Source-Only / Existing-Project-Memory-Supported / Needs-Stage3-Validation / Conflict-Pending / Tool-Gap / Example-Only / Needs-Current-Official-Verification）；`X + Y` 组合只能作依据说明；一行捆绑多个证据等级不同的子主张 ⇒ 拆原子行后全表重编号+映射。
- **历史状态词隔离**：B01 早期草稿的 Cross-Validated/Locally Reproduced 只能留在"旧草稿状态"列/纠正记录，当前状态列必须 0 命中。
- **纠错轮报告**：旧报告顶部追加 `Superseded by ...` 标记（保留原错误历史，禁止删除/重写），按指令路径新建权威报告；逐项记录"修改前/修改后"；教师指定了规范报告路径时必须用该路径。
- **存在性校验 ≠ 覆盖性校验**：locator 只验"引用有效"会漏"某 H2/H1/T 无任何卡引用"（真实事故：H2-5 无卡引用而 coverage 标 Carded，E5 反向覆盖并集检查 FAIL）。验证器须同时断言 85 卡来源范围**并集** ⊇ H1-1..81 / H2-1..430 / T-0..171 / IMG-1..13。
- **主计划编号从权威字段行解析**（`- 独立验证方案（阶段3计划 L-xx）`），不要取卡正文第一个 `L-\d+`——正文可能引用他卡 L 号造成假连续。
- **17 字段严格检查要"每卡每字段恰一次"**：锚定行首正则并允许括注变体（如 `决策步骤（逐陷阱）`），0 次或 ≥2 次都 FAIL；子串存在检查会漏变体/重名（KC-015/024/025/033 事故）。
- **验证器失败退出码**：任一 FAIL ⇒ `sys.exit(1)`，全 PASS ⇒ `sys.exit(0)`；用安全临时副本/真实失败运行实测非零退出，禁止只破坏正式文件测试。
- **状态词跨文件一致性检查的陷阱**：报告正文写"完成后将变为 Phase 2 Final Audit Closed"的未来式会被正则当成第二种状态 ⇒ 三文件状态检查 FAIL；正文只保留当前状态词。
- **audit JSON 逐卡记录**：教师要求机器可审计的 85 条 `card_reviews`（kc_id/source_locator/closest_existing_refs/matching_fields/difference_fields/category/decision_basis/stage3_plan_id），guide_card_ids 必须从 guide 文件现场解析（82 个唯一），不得手写；map 口语引用（"guide BMP 卡"）需经 speech_map 映射为规范 guide 卡 ID（映射前用关键词检索 guide 全文确认）；逐卡记录禁含 64 位样本哈希/flag/一次性值。
- **行数口径**：教师给的"1,376 行"按 `\n` 计数；`split("\n")` 因尾随空串得 1377——报告/JSON 中注明口径。
- **哈希清单冻结顺序**（防自引用不收敛）：正文修正 → 预终验（FAIL 即停）→ 冻结 → 报告登记"其他已冻结文件"哈希（自身与 final-hashes.json 不内嵌）→ 重建 final-hashes.json（含 path/size/sha256，**不含自身**）→ 最终复验 → 不再改任何文件；final-hashes.json 自身值只在交付消息给出。纠错报告描述"已删除的破损残句/旧哈希"时**不得引用残句原文或旧值字面**，否则 E12 检查又 FAIL。

- **写盘后自算哈希必须先关文件句柄**：`json.dump(obj, open(p,"w"))` 缓冲未刷即 `getsize/sha256` ⇒ 清单/回读记录记下旧值（症状：尺寸相同、哈希不同、清单一致性检查莫名 FAIL）。一律 `with open(...)` 或显式 close 后再读；同一路径二次写+追加条目的清单必须按 normcase 去重。
- **验证器新检查必须做沙箱路径审计**：读证据/结果的检查在沙箱（`--root`/`--lite` 副本）模式必须解析到沙箱副本或转 pending，禁回落正式证据目录（否则「干净副本 rc=0」探针被上一轮结果卡死）；验证器每轮自身重写的产物全部列入清单排除集，最终清单一致性在最后一次运行之后复验一次。

## 最终审计闭环轮（Final Audit Remediation / Closure）
教师对 Remediation Completed 交付做只读复核后可再发**最终审计闭环纠正指令**：新门禁（锁文件+SOURCE 双哈希+当前验证器原样运行+全部锚点+Memory）+ 状态置 `Phase 2 Final Audit Remediation Required`（保留此前 Completed 为历史自评）+ 白名单定点修复 + 增强验证器（检查数自然增至 48 项以上，不凑数）+ 冻结/哈希清单/最终复验。全条件满足才置 `Final Audit Closed`；增强验证器查出**禁改文件**（知识卡/claim/coverage/Memory 等）真实缺陷时**不得自行修复**，如实 FAIL 并输出 `Partially Completed` + 精确失败项，等训练者决定，不进入下一阶段。完整配方（E1-E13 检查清单、audit JSON schema、状态机条件）见 `references/final-audit-closure.md`。

## 阶段3 良性微型实验轮（36 项实验配方见 references/phase3-micro-experiments.md）
教师下发阶段3 指令（如"36 项良性微型实验"）后：开始门禁（锁文件 + SOURCE 双哈希含 ZIP 读 + **阶段2验证器原样运行存档必须在创建 PHASE3 目录之前** + 全锚点）→ 工具盘点（零下载：SecurityLab tools → 外部工具池 → 系统/WSL → 弘连 GoldenEyesV4 Python311 副本 pyzbar/pycryptodome）→ 四批 × 9 项连跑（批次间只落内部检查点，不等待）→ 汇总（register/results.json/claim-map/memory-candidates/checkpoint）→ 终验器（V1-V12）→ 阶段3报告 → 停止等审核。每实验协议：generator（离线合成样本+truth）+ analyzer-a/b 双独立方法 + 正/负控制 + outputs + manifest.sha256 + result.json（25 字段+断言）+ result.md；状态分级 Cross-Validated / Locally Reproduced / Tool-Gap（如实）/ Partially Validated。

## 阶段3 新增陷阱（全部来自真实事故）
- **result.json 假 PASS（L-58 事故）**：analyzer 尚未写入磁盘就生成 result.json、断言按"意图"记 True ⇒ 结果文件必须由 analyzer 真实 stdout 驱动；运行前确认 analyzer 文件存在；发现假产物立即删除重建，不得保留。
- **阶段2验证器 E10 × PHASE3 结构性冲突**：阶段2验证器 E10 检查"工作目录无 phase3 相关文件"，而阶段3 指令钦定 PHASE3=WORK\phase3 ⇒ 目录创建后阶段2验证器必 E10 FAIL。顺序纪律：门禁时刻（建目录前）原样跑 76/76 存档；此后以 final-hashes 13 项现场一致 + 越界检查（stray=[]）落实 E10 意图，并在报告中显式披露。
- **execute_code 目录循环字面量 bug**（`for s in (...): os.path.join(D, "s")` 两次事故）⇒ 写后自检循环变量名。
- **exec 沙箱 PATH 不全**（openssl/ffmpeg 等找不到）⇒ 工具定位用 glob 全盘 + 绝对路径调用，勿依赖 PATH。
- **WSL 读 Windows 文件需 /mnt/<盘符>/… 路径转换**；Windows 原生工具收 MSYS 路径不翻译。
- **json.dump truth 前 bytes 需解码/hexlify**（L-07 序列化崩溃）；f-string 表达式内禁反斜杠（Python <3.12）。
- **GUI-only 工具（CTF-NetA/PaperBack/010 Editor）无头不可交互 ⇒ Tool-Gap 并注明 GUI-only**，不猜造行为。
- **工具顶层 import 依赖缺失**：不改工具文件，运行时 `sys.modules` stub 注入可跑其不依赖该库的模式（snmpv3brute `-m` 官方向量模式 rc=0）。
- **工具副本可能占位/残缺**：0 字节 exe=损坏；aircrack-ng 包只有 GUI+DLL（核心 exe 缺失）；hashcat 无设备启动即停 rc=-1（--force 也如此）⇒ 用前验证 size/version，如实登记缺口。

## 阶段3 教师定向纠错补训轮（配方见 references/phase3-remediation.md）
教师复核阶段3 成果后下发纠错补训指令（状态改 `Phase 3 Remediation Required`，保留首轮全部历史）。流程：锁文件门禁（教师复核可能发现源被占用 ⇒ 存在就 `Paused — Source Still Open` 停止，**锁消失后从 G0 重检、不得沿用暂停前判断**）→ SOURCE/阶段2/Memory/首轮锚点现场核对 → 36 目录/文件数核对 → 全局修复（36 README + evidence_integrity 6 字段 + claims_tested 真实 ID + 状态六规范值 + 功能/审计断言分列 + manifest 全量重建）→ 工具暂存纪律（STAGED_TOOLS 最小副本 + 源/复制后/运行后哈希，首轮直接运行工具池违规如实披露）→ 11 项定向实验（负控制必须真实改变输出；物理文件+执行记录）→ 状态重算（CV+LR≥24、CV≥18）→ memory-candidates 纠正 → 增强终验器 R1-R20 → 报告。外部预置（暂停期间教师侧创建的 remediation-01/、claim-id 映射、状态块追加）经内容核验后**采用为新基线并记录时序，不得回滚**。

## 阶段3 纠错轮新增陷阱（全部来自真实事故）
- **manifest 生成后修改任何文件必须重建清单**：首轮修补 L-21/L-82 result.json 断言后未重建 manifest ⇒ 教师现场复算哈希失配。修复=登记时序（不得改哈希后声称首轮一直一致）+ 全 manifest 统一重建（387 条目全量复算 0 问题）。
- **负控制无效仍算通过是最大隐性缺陷**：L-82 "错误域"负控制不生效——简化 NTLMv2 blob 无 AV 对，域不参与 HMAC。每条负控制跑完必须核对"结果与正确路径不同"；涉及协议构造的负控制要用标准结构（AV 对/EOL）。
- **result_status 只允许六规范值**（Cross-Validated/Locally Reproduced/Partially Validated/Tool-Gap/Contradicted/Blocked）；括注移 conclusion/evidence_after，原值存 result_status_historical。
- **纯 Tool-Gap：methods_independent=false + method_na_reason + tool-gap-audit.md**；不伪造 analyzer/正负控制。`--version` 成功或 found=False 不作第二验证方法。
- **功能断言与审计断言分列**："如实报告失败"类只计 audit 不计 functional；教师点名的负控制缺失项（negative_control="无"）补齐前不得保留 CV。
- **解码评分函数三连坑**（L-63）：空格假设对重复串失效；纯数字/重复字符假阳性 ⇒ 文本评分=字母下划线占比+大写存在+数字存在，ascii 命中与 offset 爆破互斥。
- **变量名污染**：execute_code 大脚本里 `p` 既作素数又作路径 ⇒ truth 写入路径字符串；长脚本收尾统一断言/打印，防 NameError（缺 import json/re）。
- **断言自洽**：写"如实 rc"却要求 rc=0 自相矛盾；`USER::DOM` 行 split(':') 是 6 段含空段。

## 阶段3 二次纠错与技术复核轮（Remediation-02，配方见 references/phase3-remediation-02.md）
教师对 Remediation Completed 再做技术复核（状态 `Phase 3 Remediation-2 Required`，首轮报告标 Superseded 保留错误历史）。流程：门禁同前 + **manifest 现场条数与 rem-01 报告数字逐项核对**（报告写 387、现场 389 ⇒ 以现场为准登记）→ 先修验证器缺陷（V1-V9→S1-S24）→ 10 项定向协议纠错（**以规范/官方向量为准，不信自己上一轮实现**）→ 全局 36 字段审计（method_b/negative_control 非空、end_match 结构化收尾）→ memory-candidates 重建（仅 CV/LR）→ 工具暂存（新轮次独立 STAGED 目录+三哈希）→ 全部运行结束才重建 manifest → 报告。外部路径笔误（如指令写 `D:\CTF\_MISC\_Tools` 而现场是 `D:\CTF_Misc_Tools`）以现场唯一存在路径为准并登记。

## 阶段3 二次纠错轮新增陷阱（全部来自真实事故）
- **协议实现错误会跨轮存活并被教师技术复核点名**：L-81 曾在 Kul 后加 64 轮 MD5(key+0x01*64)——RFC 3414 无此迭代（64=样例缓冲块大小/HMAC pad 长）；还把"staged 工具不命中"归咎于工具，实际是**自己构造错**（工具 hex+零填充=标准 HMAC，符合 RFC）。任何协议链先锚定官方向量或真实样本，禁网时用工具池**只读真实 pcap 报文**做 A/B/工具三方闭环，不得自证。
- **L-82 类链式错误**：漏 ResponseKeyNT=HMAC-MD5(NTHash, UTF16LE(UPPER(user)‖domain))；用户名误写进 MsvAvNbComputerName（那是服务器名）；hashcat 5600 行 SC 与 NTProofStr 序反；**用户名大小写变体不是合法负控制**（ResponseKeyNT 先 Uppercase ⇒ 应同结果）。
- **analyzer 改动必须落盘**（两次事故：只在 execute_code 临时改 analyzer、只更新 result.json ⇒ 文件-结果不一致被教师点名）；改完 analyzer 必须重跑并存新输出。
- **旧输出不可变**：不覆盖 run-output.txt、不在旧输出末尾追加"v2 已通过"；新输出写 `outputs/remediation-02-analyzer*.stdout.txt`（含命令/rc）+ `remediation-02-command-record.json`（完整命令/cwd/起止/rc/输入输出哈希/工具绝对路径与哈希）；result.json 字段引用本轮新输出。
- **验证器禁 `or True`、禁假失败路径**（创建即删探针文件+硬编码 rc=1 会被教师点名）；失败探针 = 验证器支持 `--root 临时副本`，在副本制造三类缺陷（非法状态/manifest 哈希错/CV 缺 B 方法）子进程真实运行，三次 rc≠0 + 无缺陷副本 rc=0，输出存档。
- **冻结文件 byte 级恢复须二进制读写**：Windows 上 python 文本模式 `open(w)` 把 `\n`→`\r\n` 静默改哈希（误触 rem-01 验证器后回滚仍失配的根因）；恢复哈希冻结文件用 `rb/wb`。给冻结验证器标 superseded 应放**独立 notice 文件**，不得编辑 rem-01 冻结物本身。
- **证据强度规则**：恢复完整性=字节哈希全等（ffprobe 可解析≠字节完整，L-80 曾 21996≠22748 称无损）；TS CC 连续性按 PID 分组；无 RTP/应用层序号时跨 PID 全局乱序声明不可唯一恢复。
- **二进制格式细节**：ATT 多字节字段 little-endian（handle 用 `<H`）；OBEX PUT=(opcode&0x7F)==0x02（GET 0x03 不算）；av1C high_bitdepth 在 byte2 bit6（ISO 14496-15），byte0 bit7 是 marker 恒 1（曾误读致 8/10-bit 不可分）。
- **混合实验总状态=最低已验证子范围**（Fermat CV + OBEX/ATT LR ⇒ L-84 总状态 LR，子范围分别保留）。
- **自检计数/类型笔误**：`len(Counter)==36` 恒 False（Counter 键=状态种类 4）；bytes 列表 `'401' in [b'401']` 恒 False（str vs bytes）；验证器里这类条件必须用真实样例先单测。
- **验证器判据阈值别拍脑袋**：非空字段判据用"空串/占位词表"，勿用 `len<10` 字符数（会把合法短描述误判为空）。

## 阶段3 最终证据闭环与运行时交叉验证轮（Remediation-03/04，配方见 references/phase3-remediation-03-04.md）
- Rem-03：验证器从"结构审计"升级为**真实执行验证**（复制实验到临时目录真实跑 analyzer 比较 stdout/rc 与 spec；正式树只读；PASS 计数=检查项数且每项都在跑）。协议锚定 RFC 官方向量（L-81 RFC 3414 A.3 四向量）+ staged 工具真实报文正负闭环；BER 清零 msgAuthenticationParameters 用精确定位（容器内容起点/循环边界 `q<uvs+uvl` 五连坑）。
- Rem-04：**运行时显式化**——runtime-manifest.json（解释器绝对路径/版本/arch/pyc magic：3.8.6=`550d0d0a`、3.11.15=`a70d0d0a`/文件 SHA）；spec 每项 runtime_id，执行器只按 manifest 解析，禁 sys.executable 隐式；验证器由 3.8 与 3.11 两个入口启动都 24/24 才算过；L-32 固定 3.11 生成 .pyc + marshal 前 magic 预检（结构化错误码 rc=1/2/3）。子进程字节捕获（无 text=True、decode backslashreplace），输出 0 处 UnicodeDecodeError/Traceback。
- Rem-04 还废止 a_contains（CV 必须 A+B 都真实运行、compare_fields 逐字段一致）；负控制全覆盖（36/30 项，各带 decision/key_fields/`_contains`/`_not_contains`/`_neq_field` 断言）；失败探针五类（A/B 不一致/负控制换阳性/删 expected/错 runtime/二进制输出）全部 rc≠0 命中 + 干净副本双入口 rc=0。

## 阶段3 运行时可验证轮新增陷阱（全部来自 rem-03/04 真实事故，详见 references/phase3-remediation-03-04.md）
- **负控制检查只查 rc+无异常 = 假 PASS**（S11 两轮探针 rc=0 逼出）：断言必须匹配输出语义标记（键用输出真实变量名 `seq_strict_continuous`，非缩写 `strict`；`f"{k}={v}" in stdout`）。
- **A/B 输出格式不同 ⇒ compare_fields 要 pattern_a/pattern_b + kind**（equal / both_success）；提取用 group=1（group=0 带前缀恒不等）；输出含 repr 引号（`detected=['xor55']`）pattern 要容忍引号；CRLF 行尾 `\r` 使 `$` 失配（加 `\s*`）。
- **JSON 规格 regex 双转义**：经 write_file/execute_code 多层传输的 pattern 会变 4 反斜杠=字面 `\\`；修复=文件层 4→2 后再 load（勿文本替换 `\[`——非法 JSON 转义毁文件）；生成 spec 后立即 load+re.search 冒烟全部 pattern，**断言先收集真实 neg 输出再写**，禁止猜格式。
- **重复 add() 重建 spec 会覆盖丢项**（L-59 non-hid、L-83 split-token 静默消失）⇒ 重建后逐实验核对 neg control_id 清单与总数。
- **_neq_field 等标量字段必须规范化为数组**（否则逐字符迭代 neq:n/neq:t/neq:h）；断言源遍历要排除 exit_codes/accepted/decision/key_fields/_* 键自身。
- **交付消息哈希=写消息那一刻从磁盘读完整 64 位**，禁"前缀+记忆后缀"拼接（rem-03 报告哈希前缀对后缀错被点名；staged 哈希 `c098c8f3…` 记忆截断同型）；报告 §哈希表绝对路径+size+完整值、不含自身。
- **验证器中途改动 ⇒ 杀掉在跑探针重跑**（旧版结果作废）；探针脚本后台+try/except+逐条落盘（7 次全跑≈25 分钟）；每次探针 mutation 后重建副本 manifest（否则 S20 掩盖主因）；history 保留首次失败与修正，final 只汇总最终。
- 门禁锁文件出现立即停（即使 SOURCE 已 PASS）；关闭后重跑完整门禁不沿用旧判断。

## 阶段3 语义验证与严格只读闭环轮（Remediation-05，配方见 references/phase3-remediation-05.md）
教师复核 rem-04 后点名**四类验证器缺陷**：①验证器写正式树（execution-records.json/verification-summary.json 落 remediation-04）却标 S24"只读"；3.8/3.11 并行争用同一文件触发 PermissionError（教师现场 mtime 未覆盖=不得归咎教师）②S08 只查 rc+异常关键词，不读 expected_positive（错误结论 rc=0 也过）③S10 `both_success` 只证"两边输出非假值"，不是同一事实相等（L-38/46/56/58/63/66/67/69/78 九项旧映射必须纠正或降级）④S12 负控制循环体 `pass`（负控 Traceback/超时/解码错误不进 S12）。

核心架构升级（本轮全部实证 24/24 × 6 次正式运行，含双入口顺序与并发）：
- **验证器零写正式树**：`--output-dir <系统临时绝对路径>` 必填且须在 `%TEMP%` 下；落在 SecurityLab/SOURCE 目录/`D:\CTF_Misc_Tools` 内部 ⇒ **执行实验前 rc=3 拒绝**。run_id=uuid4；每实验/方法/控制独立唯一临时目录（禁 hash()/固定 ID——跨进程不稳定且可撞）。
- **S24 全树快照**：运行前后对 SecurityLab 全树（规范化 rel/size/SHA-256/mtime_ns/总数）逐项一致；新增/删除/内容/mtime 任一变化 FAIL；只比 36 manifest 或"写完相同内容"都不算只读。快照对损坏链接（WinError 1920）前后一致跳过。运行期间禁止其他进程写树（外部并发写入=环境冲突停止，不归咎实验）。
- **封装分离**：验证器成功退出后由独立 `finalize-remediation-05.py` 把临时目录规范输出复制入轮目录，记录命令/来源目标 SHA/时间——封装是显式写操作，不得冒充"验证器只读"。报告只引用最终只读复现（所有正式修改定稿后那次，且其 S23/S24 全 PASS）。
- **spec-v3 统一规范结果对象**：accepted(JSON bool)/decision(预列稳定枚举)/canonical_facts(类型化：数字保持数字、bool 保持 bool；二进制用 bytes_sha+bytes_len+Base64)/errors[]；解析失败/字段缺失/类型不符一律 FAIL；adapter 只解析 analyzer 现场输出（禁读 truth/generator），未知映射值（ELF class 非 1/2、pix_fmt 不在白名单）**拒绝不默认**。
- **S10 删除 both_success**，只允许 exact_equal / set_equal / artifact_hash_equal / mapped_equal（映射表须显式有限可审计）。九项处置：能升级出真共同核心字段的保 CV（L-38 ELF class code→bits 映射 + file/readelf 直读；L-66 坐标集合 set_equal；L-67 A 增 codec_name/sample_rate 规范输出行、frame 数 79 vs ffprobe 78 差 1 拆分记录不进共同字段；L-69 双机制 vmdk；L-78 av1C 位域→bit_depth=10 输出 + pix_fmt 白名单映射），否则**诚实降 LR**（L-46/56/58/63 的 B 只给 chunks_ok/ttl 统计/sync 头/可打印性=互补证据非同一事实）；L-32 在 A/B 输出共同 co_name/magic 后升 CV。报告给 21 项 A/B 实际值摘要，不写"均成功"。
- **S08/S09 语义断言**：A 全 30 项 + B 全 CV 项——rc∈允许值、accepted、decision、canonical_facts 每字段存在+类型+值相等、errors 空、无异常关键词；B 侧只断言 compare.facts 子集（B 不发 A 独有字段如 checksum_ok_lines/ne_64，spec expected 不能一刀切套 A 全字段）。
- **S12 all_runs**：正 A + CV B + 全部负控制 + L-32 错误分支 + staged + 辅助工具全部入列（84 条/入口实证），查 timeout/启动失败/异常关键词/缺输出/非 UTF-8 受控保存，异常数 0。
- **冻结/终验时序铁律**：所有正式修改定稿 → 重建 36 manifest → **重建 pre-manifest（全口径 579 条）** → 更新 final-hashes（S23 在复现时检查 fh vs 磁盘！）→ 最终只读复现（双入口顺序+并发）→ finalize 封装 → 再同步 final-hashes。封装产物落在轮目录（pre 不含 rem-05 ⇒ 无碍 S04），教师复现时 fh=磁盘全一致。
- 状态重算保持门槛：CV≥18 且 CV+LR≥24；降级致不达标只能 `Partially Completed`，禁止用空洞共同字段/伪造 B 保 CV。

## 阶段3 语义验证轮新增陷阱（全部来自 rem-05 真实事故，详见 references/phase3-remediation-05.md）
- **失败探针 mutation 必须先验证真会改行为**：probe1 首次 rc=0——正则 `width=(\d+)` 未命中 print 模板 `width={w}`（花括号），文件没变、探针空转；教训=改前先看目标行真实格式，探针跑完确认 mutate 生效（history 保留首次失败）。
- **adapter 字段缺失崩溃**：`int(_grab(...))` 对负控输出（无该行）抛 NoneType；拒绝类负控 canonical 断言应为空 facts 且 adapter 容错返回缺失键不抛；负控专有断言字段（crc_mismatch/contiguous/container=unknown/unrar_t_rc/frames=0/meta_texts=[]/classes）须在 adapter 里按"有则提取"补全，spec 期望值与真实输出变量名逐字对齐。
- **S09 期望值分方法**：spec expected_positive 全字段只对 A 断言；B 用 compare.facts 子集（L-49 ne_64 仅 A 有、L-66 checksum_ok_lines 仅 A 有——曾致 B 侧 missing）。
- **快照含损坏链接崩溃**（os.stat OSError WinError 1920）⇒ try/except 前后一致跳过。
- **bash 并发 `( … ) &` 语法错**（git-bash 后台无 job control）⇒ 用 Python subprocess.Popen 双进程真并发（不同 `--output-dir`），两端输出分文件。
- **execute_code 沙箱 python ≠ 运行时 python**：沙箱无 PIL（L-72 B 崩 ModuleNotFoundError），hermes venv 有——验证一律用 runtime-manifest 的绝对 python 路径。
- **二进制输出哈希**：L-01 hextext 输出原始 2 字节——对 backslashreplace 解码文本再 latin1 编码算 SHA 得错值；哈希用原始 out_b；spec bytes_sha 期望值由真实运行实算填入，禁猜。
- **输出行格式细节**：`co_name=<module>` 需 `\S+`（`\w+` 不匹配尖括号）；L-72 B 变量名是 `b_first32` 非 `first32`；负控样本真实输出（如 L-46 scale 的 decoded 非空但 meta_texts=[]）决定断言字段，先收集再写 spec。
- **pre-manifest 重建时机**：门禁冻结后任何正式修改都使 S04 失配——开发中反复 FAIL 属预期；定稿后重建（同一全口径路径集），此后验证器运行中树零写（S24 同时背书）。
- 状态词/README/result.md/result.json/register/data/claim-map/memory-candidates 七处同步一次做完（36 项实验状态改动后逐文件核对，勿只改 result.json）。

## 阶段3 最终语义真实性与异常路径闭环轮（Remediation-06，配方见 references/phase3-remediation-06.md）
教师初验 86/100，8 项硬缺陷全在"验证层假 PASS"：S08 未比 accepted/decision、S11 两分支空 `pass`、S03 `/memory/` 筛选 0 锚点空通过、S22 固定词非动态、L-80 只比 state、L-67 无帧边界证据、S09/S10 解析异常炸主程序（失败路径无 S24）、S23 清单约束不足。本轮要点：
- **observed/expected 分离**：`verification-spec-v4.json`（expected）与 `observed-rule-map.json`（每实验 field→enum→decision + accepted_map）分离；observed adapter 只读 stdout，禁读 expected/truth/generator；**rc=0 不自动 accepted=true**（L-80 loss rc=0 但 accepted=false 实测）；spec 负控 decision 值必须 == observed 在该样本上的产出（逐项对齐）。
- **S03 显式 5 锚点字典**（键集合恰 5/存在/完整 SHA），输出 `Memory anchors: 5/5 MATCH`；S08/S09/S11 全字段比较（accepted/decision/facts 类型与值/errors）；无 facts 可比的负控由 accepted/decision 证明拒绝原因，禁"没 facts 自动过"。
- **S22 动态泄漏扫描**：禁入集合现场生成（truth 值+hex 变体、样本与派生物 SHA 全值+32 截断、口令/payload 及编码变体），扫 memory-candidates 等聚合文件（不是 analyzer 证据输出）；evidence 只存 {类别,长度,自身 sha}；allowlist 逐条理由。
- **L-80 三方**（state+recovered_len+recovered_sha256 == inputs/prog.ts 逐字节）；**L-67 方案一**（analyzer-b 独立物理帧遍历 frame_count=79/contiguous=True；ffprobe 78 差异保留说明不强行相等）。
- **S24 进 finally**：成败路径都执行结束快照 + 写 summary + 异常记录；每 S 内部异常转 FAIL；快照不可访问文件（损坏 reparse 点 WinError 1920）前后一致显式记录不算变更。
- **S23**：fh 键集合含教师 15 项交付物（need 排除 fh 自身）、项数/64 位/大小约束；**每 S 编号恰一个 chk**（拆分 S08 成 4 chk 会破坏"恰好 26/26"，分项统计放 detail）。
- 12 类失败探针全命中（accepted/decision 翻转 ×4、observed 字段删除、L-80 sha 篡改、锚点缺失、注入泄漏+删除 PASS、fh 破坏、adapter 异常+finally、output-dir 禁区 ×2、干净副本）。

## 阶段3 最终语义轮新增陷阱（全部来自 rem-06 真实事故，详见 references/phase3-remediation-06.md）
- **--root 副本探针静默无效**：spec/规则/审计路径常量硬编码主树 ⇒ mutate 副本空转（probe1/2 主因永不触发）；R6 一律 `dirname(dirname(abspath(__file__)))` 推导。
- **commonpath 拒绝漏判**：只对一侧 normcase 时 Windows 上恒不等（commonpath 保留原大小写）⇒ **两侧都 normcase**（probe11b 首测 rc=1 非 rc=3）。
- **observed 取最后出现用 re.findall[-1]**：篡改探针在输出尾部追加假行，re.search 取首行永不命中。
- **subprocess "python" 解析不确定**：Runner 一律用 runtime-manifest 的绝对解释器路径（沙箱 python 无 PIL 同理）。
- **observed decision 用前缀/全值判定**：L-56 ttl64 的 ascii=b'@@@@…' 非空但非 TRAINING；L-46 scale decoded 非空但 meta_texts=[]——非空≠ok。
- **负控 method 须具备该语义**：L-18 high-entropy 挂 B（无 single_key 概念）恒错 ⇒ 改 A。
- **glob 取最新 run 按 mtime 排序**（同 prefix 多轮 run_id 随机序 ⇒ 复制到旧 summary，identical=False 事故）。
- **报告必备逐字句**：教师钦定声明句禁插括注（S26 子串检查 FAIL 事故）。
- **S23 时序死锁解**：closure-1（S23 缺键预期）→ finalize 封装 → fh 补键 → closure-2 26/26 → finalize 覆盖 → fh 同步；报告引用最后 closure，教师复现 fh=磁盘。
- 探针长跑后台+逐条落盘；验证器中途改动 ⇒ kill 在跑探针重跑；L-67 A 侧 frames= 与 B 侧 frame_count= 统一 canonical 键。

## 阶段4 闭卷、迁移与项目 Memory 晋级轮（Phase 4，配方见 references/phase4-closedbook-transfer-memory.md）
阶段4 = 闭卷 120 题 → 29 项迁移 → Memory staging/写入/泄漏扫描 → verify_phase4 F01-F26 + 12 类探针 → 统一报告。**本会话全流程实证完成（2026-09-05）**：门禁全 PASS；4A 119/120=99.17/100（错 1：Q-047 选项定位）；4B 首轮 27/29=93.1%（≥85%）→ 纠错 TR-04/TR-23 后 29/29 可复现（证据/安全错误 0）；4C 处分 29 条（4 Merge/3 Extend/8 New P49-P56/14 KMap）+ 正式写入 + 磁盘回读 + 泄漏扫描 0；验证器 F01-F26 26/26 rc=0（closure4）+ 12+ 类探针缺陷副本全 rc≠0、干净副本 rc=0；终态 `Phase 4 Completed — Awaiting Teacher Audit`（禁自写"教师通过/100/100"）。报告 `reports/misc-knowledge-summary-phase04-closedbook-transfer-memory.md` 7,996 B。按 reference 配方推进同类后续轮。
- **4B 变体生成两条路径**：genA=有 generator.py 的实验（20/29）参数化重生成——复制到 genwork（禁区）+ `TRAINING_P3_(\w+)_OK` 统一 marker 替换 + per-EXP 常量替换表（密钥/种子/素数/坐标/尺寸/占位符）；**generator 假定 inputs/ 与 negative-controls/ 已存在，genwork 必须预建**；替换目标不命中必须 warn（静默未替换=样本与 phase3 同字节违规）。genB=无 generator 的 9 项（L-11/38/59/64/67/69/78/80/81）手写构造器，先逆向 phase3 analyzer/样本校准格式再构造。
- **运行时选 py38 跑生成器**（hermes venv/uv cpython 3.11 无 hashlib md4 且 stdlib wave 有 bug；py38 有 md4+PIL+wave）——选型先双解释器探测再批量跑。
- **pack 卫生三连**：删 collector 扫入 pack 的 truth.json 副本 → truth 字符串值泄漏扫描（≥8 字符 vs pack 非 neg 字节）→ 答案承载输入（base.bin/expected-stream.ts/原始 sample）移 truth-sealed；修复型任务正样本必须真损坏（TR-03 SOF 宽高改写）；纯 truth 型 generator 的 TR 要逐项补合成输入（TR-14/27/29 实证）；负控制逐 TR maker 补齐 29/29 后重冻结 pack/truth 清单 + transfer-cutoff.json。
- **二进制构造校准实证**（RAR4 HEAD_CRC=CRC32 低 16 位/URBC 帧=`b"URB"+<BBBBH 0x43,id,dir,dev,ep>`/MP3 跳 ID3v2 synchsafe+private 位=帧头第 3 字节 bit0/VHD checksum=~sum/MPEG CRC32 非反射 0x04C11DB7/SNMPv3 authParam 12B 零占位后 HMAC-SHA1(Kul,msg)[:12]）——详见 reference。
- 4A 完成即落盘 checkpoint（含 5 Memory 起点哈希、门禁结论、4A 全部文件清单）——上下文不足在批边界停，绝不跨批。
- **门禁含三个 data/*.json 现场解析计数**（memory-candidates 恰 29、experiment-results 恰 36）+ rem-06 final-hashes **28 项逐路径现场复算** + 36 manifest 全量 0 问题；local-tooling.md 锚点若不同于阶段3 结项值，先核是否为\"合法后续变更\"（如现场验证新增工具事实）——保留不回滚、不误记污染。
- **题纸装配后必断言跨批连续**：B2 曾用 base=60+i 从 Q-061 起、B3/B4 同段撞号 ⇒ 合并后 `ids == [Q-%03d for 1..120]` 检查再冻结。四批各 30；六类全局精确 30/25/20/20/15/10（批内不必等分，全局求解器按每题候选类别集配平，勿事后改标签迁就计数）。
- **答案字母定位陷阱**：正确项位置不统一——出题把正确项几乎全放 B 的设计假设导致 Q-047（正确在 A）答错；**作答与出 key 都必须逐题回读全选项**，不按位置模式猜。从题面 regex 抽选项不可靠（题干单词含 A-D：CRC/IDAT/DTMF/AFSK/SC/Blob 干扰 `[A-D]` 切分，约 20 题 key 文本为空）⇒ key 字母表出题时即登记。
- **大批量答案写盘**：分隔符拼接串（内容含 `|` 静默截段）与元组解包（内容含引号拆列）双失败 ⇒ 直接 write_file 完整 JSON（正文引号统一用全角，避免 JSON 转义事故）。
- **CLOSED_BOOK_CUTOFF 审计**：access-audit.json 从截止点后的真实工具轨迹构建（只允许写答案文件 + 读已冻结题纸），禁自我声明。评分硬门槛：安全题 0 错 / 81 H1 / 无同误区连错 / 无禁读 / 分布精确；通过线 ≥111/120（92.5/100）。错题记错误类型+根因+KC 修订候选（只入候选，不写正式 Memory）。提交后发现作答笔误：全部批次冻结**前**可修正并记录（Q-010 A），冻结后不可覆盖。
- **checkpoint 纪律**：4A 完成即落盘 checkpoint（含 5 Memory 起点哈希、门禁结论、4A 全部文件清单）——上下文不足在批边界停，绝不跨批。

## 阶段4 完成轮新增陷阱（全部来自 2026-09-05 真实事故）
- **首轮评分须逐项人工判定**：自动\"truth 字符串命中\"扫描把结构化项（数值/布尔/坐标/图层数）误判 CHECK——truth 纯数值/布尔项、答案含相等值即 PASS；key 集合按语义逐 TR 核对后再汇总。评分只读 truth 前先确认首轮答案已冻结（哈希入档）。
- **TRANSFER_CUTOFF 禁读在首轮答案冻结后解除**：TR-23（ImageMask）穷举 10+ 编码变体全败——冻结+评分完成后才可读 phase3 generator 源码理解编码（每像素 R,G,B 各低 2 位 LSB-first，6bit/px；先前穷举缺 B 通道分量）。失败项纠错记录 remediation-results.json（first_round 原样保留 + root_cause + remediation 字段 + verdict），首轮 json 追加 remediated 键不覆盖原 answer。
- **逐 TR 求解器真实执行调试**（方法 A 输出驱动）：TR-12 AFSK 需极性×位序 4 组合重解（先跑先错）；TR-26 SNMPv3 验证端 HMAC 输入=报文 authParam 字段**清零重建**（截断前缀法错）；TR-27 ResponseKeyNT 用 UTF-16LE(UPPER(user)‖domain)（构造端裸 ASCII 拼接错⇒ truth 重算）；TR-28 NTLMSSP 需 base64 段解码后再检测（`NTLM ` 头文本内无 NTLMSSP 字样）；TR-04 IDAT 六型 truth 是机制字段（段数/流 sha/length 伪装/UNUSED 尾块），逐字段定位 sha 匹配（seg/区级 sha 枚举）。
- **4C staging 编号审计正则撞标题**：playbook 增补小节写成 `### P7 增补（…）` 会被 `^#{2,3} P(\d+)` 当新编号 ⇒ 改 `### 增补条目 · P7（…）` 消歧；P1-48 唯一性 + P49-56 连续 + Experimental 标注分别断言。
- **泄漏扫描分类放行**：`flag{` 等命中须查上下文——历史教学示例/历史教师答案记录=分类放行（非本轮写入）；SOURCE 哈希出现在 misc-index/新知识文件=指令要求元信息（放行）；真实命中（训练 marker/口令/批次文件名/一次性值）必须删。
- **验证器 F25/final-hashes 自引用闭环（同 rem-06 S23）**：final-hashes.json 必须在验证器前生成；**验证器通过后任何正式树写入（checkpoint 落盘、脚本 patch）都使 fh 过期** ⇒ 全部定稿→同步 fh→最终 closure 26/26（closure3 曾因 fh 同步在 run 之后而 F25 FAIL，closure4 才过）。探针 mkroot 复制的是旧 fh ⇒ 干净副本复核须 fh 同步后重新 mkroot。
- **探针 outdir 放 --root 副本内 = 假通过**（rc=3 执行前拒绝先触发，探针\"rc≠0 达标\"但目标检查没跑到——p1-p12 首轮全中招）⇒ 探针 output-dir 必须放 root 副本**外**（Temp 独立目录）。探针 mutate 目标键已存在=空转（p11b 覆盖 KC-001 处分后 len 仍 29）⇒ 发现验证器盲区时**增强验证器检查本身**（F21 加 New 的 into 唯一性+合法处分集合+New 必有 into），再定向复核（p11c rc=1 dup=True）。h1 缺失探针用越界值（H1-99）保证 F08 必 FAIL（H1-01 是合法编号，替换后集合比较仍可能过）。
- **报告 §10 表格哈希给完整 64 位**（从磁盘现场重算，逐文件重建表格段）；报告在最终 closure 前定稿（closure 结果印证其 F01-F26 断言），交付消息给报告/final-hashes 完整哈希与绝对路径。

## 阶段4 教师初验纠错轮（Remediation-01，教师初验 58/100，配方见 references/phase4-remediation-01.md）
教师对 Phase 4 自评交付做初验后下发纠错指令：**自评 Completed 不作有效证据，自报审计 JSON（PASS 字样）不能证明流程合规**。21 项问题四域：闭卷（选项分布 A=2/B=118 固定全选可过线 ⇒ 新题 A/B/C/D 各 30±2 随机；H1 覆盖须验题意非编号；同主体出题+作答=记忆污染 ⇒ **无教师独立题包则闭卷只能 Pending，终态 `Partially Completed — Awaiting Independent Closed-Book Pack`**）；迁移（observation 必须逐 TR 严格 1→8 实时落盘禁批量补日志；评分须程序从密封 truth 独立比较，首轮最多 22/29 判定）；Memory（post-Phase4 归档隔离→正式 Memory 恢复 pre-Phase4 或标 Quarantined，门禁全过后才重新晋级；Playbook 每条 12 字段全（含失败回退/安全边界）；无原子依赖主题禁合并成一条 P；索引≠完整卡；training-progress 禁存真实答案 flag）；验证器（不信 fh/分数自报、F04 前缀哈希/F10/F18 信 PASS 串等 11 处缺陷全修、探针缺陷副本必须失败项含目标检查、每次运行原始输出落盘作证据、final-hashes 之后零写入——closure 26/26 后 checkpoint 落盘未同步 fh ⇒ 教师现场 F25 的实证）。
- **v2 全新变体重生成**：EXTRA 替换 old 值必须=generator **原文**（非上轮已替换值，12 MISS 事故）；转义层数/grep 实际写法/MISS=0 硬门禁；重生成后树级哈希 vs 归档首轮零复用断言 29/29；样本/truth 内部一致=修生成器不修 truth（TR-21 帧数≥消息位数断言、TR-24 av1C bit6=high 0x40=10-bit）；neg 补齐 18 项按语义映射破坏型；task.md 口径冻结先行（TR-05 块边界/TR-16 停止位/TR-23 位长/TR-25 PES 长度/TR-18 全消息）。
- **终态机**：无独立题包 ⇒ `Phase 4 Remediation Partially Completed — Awaiting Independent Closed-Book Pack`；全部硬门槛真实通过才可写 `Phase 4 Remediation Completed — Awaiting Teacher Final Audit`；不开始下一阶段、不写 Hermes 全局 Memory。

## 阶段4 纠错轮迁移重跑与作答执行（Rem-01 批次 2-3，配方见 references/phase4-remediation-01-answering.md）
教师初验后 29 项 v2 全新样本重生成→作答→独立评分实测 **25/29=86.2%（≥25 过线），证据/安全错误 0**，4 项诚实 FAIL 留纠错轮。核心纪律：
- **严格 1→8 observation**：obs() 断言步序严格递增；step 2..7 的 obs 调用必须在多文件循环**外**（循环内重发步=断言崩）；修复后重跑必须清 log+结果全量重跑（每 TR 恰 8 条检查器硬断言）；批文件 py_compile 失败=静默零输出（f-string 反斜杠，<3.12）——`grep -c FAIL`=0 不是成功，核对答案文件数。
- **独立评分**：逐 TR 手写比较器程序比对 truth（规范化规则预冻结）；周期 XOR 密钥按整倍重复规约后再比；答案冻结（29 文件哈希）先于开 truth；多轮修复后重跑必重评分防回退（s25 语法错曾致 19/29）。
- **solver 解析事故簇**（详见 reference）：pcap Ethernet 头 14B 偏移（sport@34/TTL@22）；MPEG-TS AF 控制=2 bit（0x10 无 AF）、PES 头 9B（plen 含 3B 标志）、跨 PID 文本按全局包序重组+滤纯 NUL PES；AFSK 用窗过零率判决（cos 投影非整周期失效）；URBC 帧无长度字段（逐 pcap 包解）；NMEA GPRMC 坐标在 fields[3]/[5]；SNMPv3 engineID=用户名前最早的 04 0c。
- **精确容量载体**：隐写载体位数==消息位长（图 4×6px×6bit=18B），否则消息后随机低位"看似可打印"令截断规则失效；样本缺陷修 generator 不修 truth；正文修改后重冻结（cutoff supersedes 链注明原因）再作答。

## 阶段4 纠错轮收尾（Rem-01 批 4-6 实证：纠错 29/29、Memory 撤回、验证器 v2，配方见 references/phase4-remediation-01-batches46.md）
教师初验 58/100 后的迁移/验证器闭环在本会话完整实证：
- **纠错轮解码配方**（禁读期结束读 generator 源码一次命中）：TR-13 MIDI note 承载 `note=0x40+b%0x60`（vel=0x60 标记；<0x20 字节 +0x60 恢复模歧义）；TR-16 PT2242 帧=同步(1,31)+20bit addr+4bit data+停止，脉宽 0=(1,3)/1=(3,1)，帧长 132 电平；TR-17 URB 帧=`"URB"+0x43+id+dir+dev+ep(<H)`（**不是 URBC**——帧签名以 generator 现场代码为准，不沿用上轮记忆）；TR-26 SNMPv3 m2 重建**保留 04 0c tag**（`msg[:ap+2]+00×12+msg[ap+14:]`）+ engineID=用户名前最早 04 0c。评分器比较键必须对 answer 真实字段名（msg1/msg2 ≠ msg 事故）。
- **Memory 撤回**：post-Phase4 7 文件归档（+manifest）→ staging 重建核对 → 正式恢复 → 磁盘回读 5/5；pre-Phase4 基线源=**4C 应用前备份**（phase4/memory-backup），教师指令后的门禁快照备份是 post-Phase4 状态不可作基线。重新晋级须等闭卷+迁移门禁全过。
- **验证器 v2（F01-F20）**：F04 完整 SHA+新文件移除断言；F05 闭卷作废/Pending（勿写自创 split 否定逻辑）；F06-F08 sha256 清单逐行解析核对 SHA+大小；**F15 泄漏扫描范围=Memory/记录区（pack/answers 天然含解码产物；SOURCE 哈希=元信息放行）**；F17 计数从运行记录文件读。正式树 20/20 rc=0。
- **探针目标命中铁律**（v1 首轮 12 探针全假通过）：outdir 放 --root 副本内=rc=3 先触发假达标 ⇒ 放副本外；mutate 必须使目标检查独中（泄漏注入记录区文件而非 memory——后者 F04 先 FAIL）；p11 outdir 在回调内自断言 rc==3；p12 异常=坏 JSON ⇒ rc≠0+stdout 含 FINALLY_SNAPSHOT MATCH；clean rc=0 是套件有效必要条件（fh 过期致 clean rc=1 时重 mkroot）。

## 阶段4 盲测架构重建轮（Rem-02，教师复验 72/100，配方见 references/phase4-remediation-02.md）
教师判定迁移首轮/纠错全作废（solver 含一次性 marker=先验污染、方法 B 非独立、observation 自报）。重建核心：**analyzer A/B（58 函数双集合）冻结先于样本生成**——零 marker/truth 常量（grep 断言 0 命中），判定只用格式不变量与通用可打印性；机制参数外置 params.json（样本常量如 user 名必须 params 化，替换保持 if 缩进）；comparison spec 类型化预冻结；执行包装器自动 observation（run_id/入口+输入哈希/起止/rc/输出哈希，业务 analyzer 零自报）；neg=同名损坏文件；密封后盲测作答+spec 评分。本会话实证：**首轮 21/29**（A 侧独立通过 21；FAIL=TR-10/17/18 真解 + B 五项实现缺陷致 AB 一致性未过），评分器 4 轮迭代收敛。高频陷阱：wrapper `text=True` 必须显式 `encoding="utf-8"`（GBK 崩乱码输出静默丢结果）；stdout 取最后非空行；**collector walk 泄漏 truth.json 第三次复现**（修收集逻辑非只清理）；neg 同名损坏（UTF-8 崩=失败特征，rc!=0 记通过）；单产物 TR 输入从 genwork generator 源码常量重建（不重跑）；OBEX 头=tag 先 len 后（len 含自身）；TR-04 双 zlib 流=段数据 0x789c 起始开新流；评分器三层键名映射（truth 实际键/spec 键/core 键）+hex_0x int 用 format(x)+周期密钥减半规约+剥帧标志；truth 契约核对（input_hashes fallback 须按任务语义重建）；写代码字符串内嵌 ''' 三引号冲突；行替换出乱改函数边界整体重写。

## 独立闭卷题包作答轮（教师下发 Pack zip，240 题全量提交实证，配方见 references/closedbook-pack-answering.md）
教师下发独立闭卷题包（`Pack-X-public.zip` 附件、含 PACK-METADATA / QUESTION-SPEC / samples，密封答案在教师侧）= 解除 `Awaiting Independent Closed-Book Pack` 的事件。流程：只读哈希+列包 → 解压受控副本（zip 原样不动）→ 读 QUESTION-SPEC.json → 分批作答（每批 20-30 题）→ 累计提交 `submissions/pack-X-responses.json` → 三类完备性校验 → SUBMISSION-REPORT.md → 提交后状态=等待教师按密封规则评分（**不得自评通过**）。
- **样本先抽查再决定投入**：本类 samples/ 为题面逐字转录（record 文件）⇒ 作答=对题面数值的推理判断，无需逐样本解析；抽查一个确认即可。
- **提交契约**：`{"prohibited_source_violation": false, "responses":[{"question_id","answer","evidence","boundary_statement","alternative_explanation"[,"safety_acknowledgement"]]}`；四段式=判断结论 + 题面证据（字段/偏移/记录号）+ 证明边界（仅证明 A 不证明 B）+ 其他解释；spec `safety_gate=true` 的题必须附 safety_acknowledgement。
- **三类完备性校验（程序化）**：safety_gate 集合 ⊆ 带 ack 的响应集合；四必填字段非空；期望 ID 全集（生成式构造，禁手打）无缺号。
- **报告转录值现场回读**：zip 大小 / freeze_id / sample_count 等先核对磁盘再写入；哈希现场实算完整 64 位（禁前缀+记忆拼接）。

## 正式 Memory 受控晋级与最小闭环修复轮（Memory Promotion & Hygiene，配方见 references/memory-promotion-hygiene.md）
训练者下发「正式 Memory 受控晋级」或对晋级成果追加「最小闭环修复」指令时走本流程；两轮同源不同焦点，产物根 `memory-promotion-v5/`（修复轮落 `hygiene-fix/`）。
- **第三种轻量轮 · case 复盘固化**：实战 case 收题后把「原题 + 迁移变体验证过」的通用经验并入既有编号体系——**合并/扩展优先，仅无对应条目才新增 P 编号**；先备份 + 记录全店前哈希 → 在址编辑 → 编号连续性/重复检查 + 受限泄漏扫描（排除备份目录）+ 后哈希 `sha256sum -c` 回读 → 单报告 + 指令终态串后停止。完整配方见 `gated-knowledge-promotion` 技能「Lightweight in-place variant」一节。
- **晋级轮**：门禁 → 候选清单从证据重生成（处分七类：New/Merge/Extend/知识地图/来源限定/工具缺口/Reject）→ 泄漏+冲突审计 → 备份+staging+原子替换+磁盘回读+回滚演练 → **新会话部署冒烟**（delegate_task 全新会话只读正式 Memory 作答；对照题必须如实回「未收录（cannot verify from memory）」，禁先验补答）→ 增强验证器+失败探针 → 报告/sidecar/最终清单 → 终态字符串并停等审核。
- **修复轮**：冻结（活跃 Memory+证据全树）→ 含真实答案值历史文件只读归档（`attrib +R`，历史不删）→ 活跃值定点替换为占位符 → **全量全文泄漏扫描（非增量，含编码变体）** → 候选元数据修正+程序化一致性核对 → 更新索引/报告补记/sidecar/清单/回读 → 增强验证器（含全量扫描、处分语义两项新硬检查）+ 全部探针重跑。
- **候选处分口径（处分↔目标语义一致）**：Reject=目标空+保留理由；New Playbook=目标指向新建 P 编号（须在新增区、全 New 恰为该区全集）；Merge/Extend=目标 P 存在（Extend 须含「晋级轮补充」标记）；KMap/SO/Tool-Gap=总结 §N+关键词。每条候选带结构化「目标定位」（文件/定位符/核验关键词），验证器现场复算 N/N；落点其实不存在的条目不新增正文凑一致，按真实落点改写目标。
- **授权变更账目化**：新轮合法改动旧验证器冻结文件时，不削弱检查、只改期望基线——override 为修复后参考副本 + 旧基线（staging）字节冻结断言 + 「与上一轮记录差异集合==授权集合」逐文件断言。
- **活跃 Memory 禁含真实答案值**（历史轮已判违规一次）：修复=占位符替换+只读归档+全量扫描（原文/令牌/base64/hex/反转/大小写变体；扫描器与证据只存哈希签名，不落明文）；历史存在点（报告/既有证据副本）只登记不修改。豁免项（工具二进制哈希/既有去重键/术语与路径命中）逐条登记放行，硬指标=未授权 0；每文件设十六进制命中预算，超预算即 FAIL。
- 更新脚本必须幂等（报告追加/索引行替换加「已应用」守卫）——清单常因后续修复重建、脚本会重跑；终态字符串按指令原文（Pack C/闭卷类写「训练者豁免」，禁 Passed）。

## 支持文件
- `references/memory-promotion-hygiene.md` — 正式 Memory 受控晋级与最小闭环修复轮完整配方：两轮骨架与脚本序列、定点替换纪律、全量泄漏扫描设计（变体哈希签名/候选解码/逐文件十六进制预算/分类放行表）、候选处分↔目标语义表与程序化核对、授权变更账目化三件套、新增硬检查（全量扫描/处分语义）与对应探针（变体注入/目标篡改的检查隔离）、工具工程陷阱（关句柄再哈希/沙箱路径审计/幂等更新/生成器式脚本反斜杠审计）、交付五件套与终态纪律。
- `references/closedbook-pack-answering.md` — 独立闭卷题包作答与提交流程（Pack-A/B 240 题全量实证）：包结构与只读读取、QUESTION-SPEC 字段、批循环与 put() 幂等落盘、四段式答案规范、safety_gate 完备性校验、报告转录值核对。
- `references/phase4-remediation-02.md` — 阶段4 盲测架构重建轮完整配方（教师复验 72/100，2026-09-05，首轮 21/29 实证）：analyzer A/B 冻结纪律（零 marker 动态扫描/格式不变量/params 外置）、A/B 独立实现对照表、执行包装器（UTF-8 显式解码/最后非空行/rc!=0 诊断）、pack 泄漏三连发根因与 neg 同名损坏、单产物 TR 输入重建、OBEX 头序、TR-04 789c 双流分组、评分器三层键映射与规约（hex_0x int/周期减半/剥 ~）、truth 契约核对（input_hashes fallback 重建）、事故簇与剩余纠错清单（TR-10/17/18 + B 五项）。
- `references/phase4-remediation-01-batches46.md` — 阶段4 纠错轮收尾配方（批 4-6 实证，2026-09-05）：四项解码配方（MIDI note 承载/PT2242 脉宽/URB 帧签名/SNMPv3 04 0c tag 保留）、评分器键名事故、首轮证据冻结与覆盖披露、Memory 撤回与 pre-Phase4 基线选源（4C 前备份非门禁快照）、验证器 v2 F01-F20 要点、探针目标命中铁律（outdir 副本外/mutate 独中/p11 rc==3/p12 坏 JSON+finally/clean rc=0）。
- `references/phase4-remediation-01-answering.md` — 阶段4 纠错轮迁移重跑与作答执行配方（25/29 实证，2026-09-05）：4 批求解器架构、严格 1→8 observation 纪律、独立评分与周期密钥规约、solver 解析事故簇（pcap Ethernet 偏移/MPEG-TS AF 2bit+PES 9B/URBC 逐包/过零率 AFSK/NMEA RMC/SNMP engine 定位）、精确容量载体设计、批执行陷阱、4 项诚实 FAIL 记录。
- `references/phase4-remediation-01.md` — 阶段4 教师初验纠错轮完整配方（教师初验 58/100，2026-09-05）：21 项问题逐条（A 闭卷六/B 迁移四/C Memory 六/D 验证器五）、纠错执行顺序（冻结同步→独立题包闭卷→迁移重跑→验证器重建→Memory 重新晋级→报告十项）、v2 全量重生成技术（EXTRA 原文替换/转义/MISS=0/树级零复用断言/样本-truth 一致性修复/neg 补齐/task 口径冻结）、本批事故记录。
- `references/phase4-closedbook-transfer-memory.md` — 阶段4 完整配方（4A 闭卷 119/120 + 4B 用例生成实证，2026-09-05；4B 首轮作答/评分与 4C/验证器待执行，须按教师指令推进）：门禁细节（含 local-tooling 合法变更处置）、题纸/题map/批次装配、截止点与审计、评分与硬门槛、错题分类、4B 生成两条路径（genA generator 参数化替换表 + genB 9 项手写构造）、二进制格式校准（RAR4 CRC32 低 16 位/URBC 帧布局/VHD ~sum/MPEG CRC/SNMPv3 BER authParam 链）、pack 卫生三连与泄漏扫描、TR 输入审计与补造、TR-01..29 ↔ 29 候选映射表、4C（candidate-disposition 五处分/staging/备份/回读/泄漏扫描）与 F01-F26 规划。
- `references/phase3-remediation-02.md` — 阶段3 二次纠错与技术复核轮完整配方（18/18 实证，2026-09-03）：门禁与 389-vs-387 失配案例、10 项定向协议纠错的正确链与规范锚点（SNMPv3 USM/NTLMv2/OBEX/ATT/TS/av1C）、V1-V9→S1-S24 验证器重建逐项、`--root` 三类失败探针真实 rc、输出不可变与命令记录规则、工具暂存 rem-02 目录三哈希、冻结文件二进制恢复纪律、交付物清单。
- `references/execution-playbook.md` — 各阶段配方、验证脚本要点、陷阱目录与事故→教训对照。
- `references/final-audit-closure.md` — 最终审计闭环轮完整配方：门禁清单、E1-E13 增强检查、audit JSON 85 条逐卡 schema、冻结/哈希清单顺序、状态机与禁改文件缺陷处置（含 H2-5 案例）。
- `references/phase3-micro-experiments.md` — 阶段3 微型实验轮完整配方：36 项实验 10 文件协议、双方法独立与正/负控制规则、状态分级、result.json 25 字段 schema、V1-V12 终验器检查项、批次纪律与报告要点（36/36 实证，2026-09-02）。
- `references/phase3-remediation.md` — 阶段3 教师定向纠错补训轮完整配方：门禁重检纪律、教师 11 类全局缺陷模板、11 项定向实验通用改法（负控制有效性/评分函数/诚实分级）、工具暂存纪律、R1-R20 增强终验器逐项、状态重算门槛与交付物清单（20/20 实证，2026-09-03）。
- `references/phase3-remediation-03-04.md` — 阶段3 最终证据闭环（rem-03）与运行时交叉验证（rem-04）完整配方：验证器真实执行升级（临时目录运行+spec 比较）、runtime-manifest 双入口协议（pyc magic/禁 sys.executable）、L-32 magic 前置结构化拒绝、字节捕获、compare_fields 正确形态、JSON regex 双转义修复、S11 语义断言（_contains/_not_contains/_neq_field）、五类失败探针执行纪律、交付哈希完整值纪律（24/24 双入口实证，2026-09-03）。
- `references/phase3-remediation-05.md` — 阶段3 语义验证与严格只读闭环轮完整配方（24/24 × 6 次正式运行实证，2026-09-04）：四类验证器缺陷定案、严格只读架构（--output-dir 外置/执行前 rc=3 拒绝/全树快照含 mtime_ns/uuid 隔离/并发双进程/封装分离）、spec-v3 规范结果对象与只读 adapter、S10 比较类型矩阵（exact/set/artifact_hash/mapped_equal + 九项旧 both_success 处置表）、S08/S09 语义断言与 B 侧 compare.facts 子集、S12 all_runs 全量清单、冻结→复现→封装→final-hashes 时序、五类探针（含 probe1 首轮空转教训）、状态重算 CV18/LR11 结果。
- `references/phase3-remediation-06.md` — 阶段3 最终语义真实性与异常路径闭环轮完整配方（S01-S26 顺序/并发/closure 全部 26/26 实证，2026-09-04）：8 项硬缺陷定案、observed/expected 分离与 observed-rule-map 设计、S03 显式 5 锚点/S08-S11 全字段比较/S22 动态禁入集合/S23 键集合约束、S24 finally 异常路径快照、L-80 recovered 三方与 L-67 独立物理帧遍历强化、12 类失败探针执行要点、陷阱目录（--root 副本常量 __file__ 化、commonpath normcase 双侧、findall[-1]、负控 method 语义、逐字声明句、S23 时序死锁解）。
