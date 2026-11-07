# Phase 4 教师初验纠错轮（Remediation-01）配方

> 2026-09-05 · 教师初验 58/100 → `Phase 4 Remediation Required（闭卷有效性、迁移评分、Memory 晋级与验证器均未闭环）`
> 触发：教师下发 Phase4 定向纠错指令（同型附件）。核心判词：**"两道能力门禁均不能由现有证据证明通过，项目 Memory 晋级因而无效"**——自评 Completed 不作为有效证据，自报审计文件不能证明流程合规。

## 教师 21 项问题归类（issue-register 逐条登记格式：问题/确认/处置）
- **A 闭卷**：A1 正确选项分布 A=2/B=118（固定全选 B=118/120，能力分数作废）；A2 H1 覆盖只验编号不验题意（Q-038 起错位）；A3 作答字母与语义矛盾不得只按字母评分；A4 答案表占位文本+来源只到 H1 级（须 P-/T-/IMG- 细粒度）；A5 access-audit 自报 PASS 不算禁读证据；A6 同主体出题+作答=记忆污染 ⇒ **无训练者独立题包则本项只能 Pending，不得自宣布通过**。
- **B 迁移**：B1 observation-log 197 条但 step 分布不成 29 个严格 1→8 序列（7=0、批量追加）；B2 transfer-access-audit 自报 PASS 无效；B3 八项结果与 truth 不一致却判 PASS（TR-18 部分消息空/TR-21 8/10B+样本容量与 truth 内部不一致/TR-23 多尾部/TR-25 前缀+0xFF/TR-29 OBEX Body 空/TR-24 结构化 8-bit 结论写 10-bit 自相矛盾/TR-16 位数口径/TR-05 尾部残留）；B4 程序独立评分后首轮最多 22/29 < 25/29。
- **C Memory**：C1 门禁未过则 P49-P56/新知识文件/Merge/Extend 不得保留"已晋级"；C2 先归档 post-Phase4 Memory 为隔离证据，再从 memory-backup 重建 pre-Phase4 基线核对哈希，门禁全过前正式 Memory 恢复 pre-Phase4 或标 Quarantined/Unvalidated；C3 P50/51/52/54/55 缺失败回退/安全边界字段（每条须 12 字段：触发/适用条件/最小证据/步骤/停止条件/失败表现/回退/替代解释/安全边界/验证方法/证据等级/来源）；C4 P56 三主题无原子依赖合并成一条 ⇒ 拆独立候选，编号连续唯一不凑数；C5 索引≠完整卡（要么明标索引+逐项链接，要么补完整字段）；C6 training-progress.md 含真实教师答案 `flag{...}` ⇒ 改为不含答案正文的历史描述（通用 `flag{}` 格式说明与具体答案区分）。
- **D 验证器/报告**：D1 现场 25/26 F25（final-hashes 登记 checkpoint.json 380 B 现场 983 B）；D2 probe-results clean=rc1/closure3=rc1 且无 closure4 记录（claim 无证据，报告"clean rc=0/closure 26/26"撤回）；D3 探针 p3 只触发 F25 未触发目标 F08；D4 验证器自查缺陷清单（F04 哈希前缀检查/F10/F18 信 PASS 串/F12 无来源语义/F13 信自报分数/F17 只数 step=1/F19 只查非空/F20 信自报/F22 未把检查纳入判定/F24 禁入集合窄/F25 不核对大小/F26 计数硬编码）；D5 交付摘要手写占位哈希 ≠ 现场值（转录错误）。

## 纠错执行顺序（教师钦定）
1. **冻结与状态同步**：独立 remediation-01 目录（snapshots/：pre-remediation 全树清单+Memory 备份+manifest+验证器现场原始 stdout/stderr/EXIT）；原报告/checkpoint 只追加 superseded+Required 状态（正文保留）；不建独立教师校验表。
2. **闭卷重立**：等训练者独立未见题包（SecurityLab 不参与生成答案）；120 题 A/B/C/D 各 30 或最大偏差 ≤2 随机排列（禁单一选项策略过及格线）；每题答案有语义+最小证据+P-/T-/IMG- 来源定位；答案密封后新隔离会话作答，存系统真实工具轨迹/读取路径/时间/哈希；独立评分器从 answer-key+responses 重算（不信自报 score）+字母与语义双一致性。**无题包 ⇒ 终态只能 `Phase 4 Remediation Partially Completed — Awaiting Independent Closed-Book Pack`**。
3. **迁移重跑**：修 TR 样本/解析边界/truth 内部不一致；每 TR 全新良性变体+负控制（**零复用首轮正样本字节**）；observation 严格按 1→8 实时落盘（缺步 FAIL，禁事后补日志）；A/B 真实运行比同一核心事实（互补证据≠交叉验证）；规范化规则预先冻结（看到结果后不得放宽）；首轮 ≥25/29 且证据/安全错误 0 才可晋级 Memory。
4. **验证器重建**：只读正式树+显式外置 --output-dir；全量现场 SHA+大小（不信 fh 自报）；选项分布/随机性基线/"固定单选不得过线"；逐题语义来源定位；答案独立重评分+语义矛盾；截止后真实访问轨迹；29 TR 严格 1→8；A/B 真实执行与核心事实比较；truth 精确评分及纠错复现；候选/处分/证据等级/Playbook 完整字段与原子性；动态泄漏扫描覆盖完整 flag/答案/truth/marker/口令/URL/哈希及 hex/base64 变体；运行前后 SOURCE/SecurityLab/Memory 快照一致；资源计数从运行记录计算禁硬编码。**缺陷副本必须失败项含目标检查；干净副本 rc=0；验证器异常 rc≠0 且 finally 仍完成只读快照**。
5. **Memory 重新晋级**：门禁全过后从 staging 生成候选差异；逐条 Merge/Extend/New/Map/Reject，只把真实通过内容标 Experimental；完整回读+字段审计+P 编号唯一+动态泄漏扫描后才原子写入；写入后现场重算大小+完整 SHA；**最后生成 final-hashes，之后不得再修改其登记对象**。
6. **报告十项**（初验前后对照/验证器原始输出/旧题作废与新题包/29 项逐项 truth 比较/撤回重建与泄漏/增强验证器与探针/全部文件绝对路径+大小+完整哈希/起止锚点/实测计数/未解决项与证据边界）。

## v2 全新变体重生成技术（实证）
- **参数化替换（genA）**：EXTRA 替换表 old 值必须=**phase3 generator 原文**（未替换过的 TRAINING 原始文本），不是上一轮已替换值（12 MISS 事故：把 v1 值当 old）；转义层数坑（raw 字符串 4 反斜杠=字面双反斜杠 ≠ 文件内单反斜杠 `b"\xAA"`，须 grep 文件真实文本再写 old）；IP/常量先 grep generator 实际写法（L-83 是 `10.0.0.x` 变量非 `10.10.10.x`）；**MISS=0 是硬门禁**，静默未替换=与首轮同字节违规。
- **零复用验证**：重生成后对每个 TR 做树级哈希（rel+内容 sha 拼接）与归档首轮（round1-transfer-archive/，物理移动保留证据）比对，29/29 必须全不同。
- **样本/truth 内部一致性**：TR-21 帧容量 < 消息位数 ⇒ 嵌入截断（修生成器 duration+`frames ≥ len(msg)*8` 断言，truth frames=232 与样本一致）；TR-24 av1C byte3 bit6=high_bitdepth（0x40=10-bit；0x80=bit7=seq_tier）⇒ 修生成器构造使样本与 truth 一致（意图明确时修样本/生成器，不修 truth）。
- **负控制补齐**：18 项缺 neg（generator 不自产）⇒ 按 TR 语义映射破坏类型（trunc/flip/head/tail），坏后字节须 ≠ 原样本。
- **task.md 口径冻结**：教师点名项全部写入 task（TR-05 块边界=size 字段精确切/TR-16 bits=24 不含停止位/TR-23 6bit/px 精确位长/TR-25 PES_packet_length 精确/TR-18 全 5 消息非空/TR-24 位深位/TR-29 OBEX Body 非空）——规范化规则先冻结，结果出来后不得放宽。
- 新冻结：solver-pack.sha256（131 文件）/truth-sealed.sha256（29）→ `transfer-cutoff-rem01.json`（forbidden_after 含 round1-transfer-archive）。

## 本批事故记录
- genA mkdir 缺失（v2 去掉 inputs 预建 ⇒ 18 项 FileNotFoundError）——generator 假定 inputs/ 与 negative-controls/ 存在。
- sha() 收 bytes 参数（open(bytes) 路径解码崩）——isinstance bytes 分支。
- probe outdir 放 root 副本内=rc=3 假通过（与 rem-01 教师批 p3 同根：探针必须让目标检查真实 FAIL）。
- 教师 D1 现场复现：closure4 26/26 后 checkpoint.json 更新（380→983 B）未同步 fh ⇒ 教师现场 25/26 F25——**最终 fh 之后零写入**；验证器每次运行（含失败）都要落盘原始输出与 rc 作为证据。
