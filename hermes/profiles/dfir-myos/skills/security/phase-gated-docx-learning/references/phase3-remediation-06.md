# 阶段3 Remediation-6：最终语义真实性与异常路径闭环轮（26/26 实证，2026-09-04）

教师对 rem-05 复核初验 86/100，点名 8 项硬缺陷；本轮验证器从 S01-S24 扩为 **S01-S26**
（新增 S25 CV 主张—事实相关性审计、S26 报告/状态/声明一致），正式运行 = 顺序双入口 +
并发双入口 + closure 复现全部 **26/26 PASS、rc=0**；12 类失败探针全部命中；全树快照每次一致。

## 一、教师复核认定的 8 项硬缺陷（须在报告 §一 如实记录，不得改写）
1. S08 只比较 rc/异常/canonical_facts，**未比较正控制 accepted/decision**（spec 里有字段但没比）。
2. S11 对负控制 accepted/decision 的两个分支是**空 `pass`**——实际未校验；canonicalize 返回的 facts 也无统一 accepted/decision。
3. S03 用 `if line and "/memory/" in line` 筛 pre-manifest——清单路径是 `memory/xxx`（无前导斜杠）⇒ 现场 0 锚点却 PASS。**空集合通过是缺陷**。
4. S22 只搜 6 个手写固定词，不是动态泄漏扫描；未扫 memory-candidates 本体。
5. L-80 A/B 只共同确认 `state=COMPLETE`（分类一致≠恢复字节相等）。
6. L-67 A/B 只共同确认 codec/sample_rate（格式参数≠物理帧边界连续性）。
7. S09/S10 解析异常直接抛未捕获异常退出 ⇒ S11-S24 不执行，**失败路径没有 S24**。
8. S23 只抽查存在性，键集合/项数/64 位/大小约束不足。

保留不改：L-80~L-84 主体结论、双入口与 L-32 固定 3.11、字节捕获、--output-dir 外置架构、
36 项实验与状态起点（起点≠本轮预设答案）。

## 二、observed/expected 分离与规范结果对象
- `verification-spec-v4.json` 只含 expected；`observed-rule-map.json` 逐实验记录
  `{field, enum_map, accepted_map}`：observed adapter 从 stdout 提 field → 查 enum_map 得 decision →
  查 accepted_map（独立于 expected spec）得 accepted。
- **rc=0 不自动 accepted=true**（L-80 loss 样本 rc=0 但 accepted=false 实测）；同一退出码不同语义按证据字段区分；
  accepted=false 不自动等于某固定 decision；`errors` 由实际执行产生。
- observed adapter 禁止读 expected/truth/generator/旧 result.json；未知枚举/缺字段/类型错/解析失败一律 FAIL（不默认补齐）。
- spec 负控 expected 的 decision 值必须 == observed 在该样本输出上产出的值（逐项对齐，如 L-01
  `ascii_plaintext`、L-02 `insert_applied`、L-11/L-64 `rejected`、L-82 `wrong_password`、L-49/L-83 负控同输出时 decision=ok）。

## 三、S03/S08/S11/S22/S23 修复要点
- **S03**：显式 5 项 相对路径→哈希 常量字典；断言键集合恰为 5、每项存在、完整 SHA 相等；输出行
  `Memory anchors: 5/5 MATCH`。root 副本模式下锚点基准=base（副本 memory/），否则探针无法触发 FAIL。
- **S08/S09/S11**：每控制比较 rc∈允许值 + accepted + decision + canonical_facts（键集合/类型/值）+ errors 空 + 无异常。
  S08 用 expected 全字段（A 独有字段如 L-66 checksum_ok_lines、L-49 ne_64 只对 A）；S09 用 compare.facts 子集对 B。
  无 facts 可比的负控（L-18 high-entropy、L-33 truncated、L-72 noise、L-81/82 wrong-pw）必须由 accepted/decision
  实际观察值证明拒绝原因，不得"没 facts 就自动过"。
- **S22 动态泄漏扫描**：现场生成禁入集合——36 truth 值及 hex 变体、输入样本与派生物完整 SHA-256 + 32 截断 +
  显著前缀、样本专用口令/密钥/消息 payload（snmp_password、70336b39、nthash 等）及 hex/base64/URL 编码等价形式。
  扫描目标 = memory-candidates.json / experiment-results.json / claim-experiment-map.json（**不是 analyzer 证据输出**——
  证据输出允许保留）。`leak-scan-evidence.json` 每条禁入只存 {来源类别, 长度, 自身 sha256}，报告不得重复泄漏原值；
  命中给出 {目标文件, 行号, 来源类别, 值 sha}。allowlist 逐条给理由（TRAINING_P3 前缀=良性样本训练消息标识符，
  证据输出允许；memory 候选层仍禁入具体 payload 值）。探针：注入一次性值 ⇒ S22 FAIL；删除注入干净 ⇒ PASS。
- **S23**：final-hashes 必须存在；键集合须含教师 §十四 15 项交付物（**need 排除 final-hashes.json 自身**——
  fh 不含自己，S23 若要求含自己键永不收敛）；缺键/缺文件/非 64 位哈希/错误大小全 FAIL。
- **每 S 编号恰一个 chk() 调用**：把 S08 拆成 accepted/decision/facts/rc 四个 chk ⇒ 总数超 26 破坏"恰好 26/26"；
  分项统计放 detail 字符串（`accepted=29/30 decision=…`）。

## 四、S24 异常路径（finally）与快照
- 顶层 try/except/finally：运行前先快照；主体内异常 → 写 exception-record 并转 FAIL；finally **无论成败**都执行
  结束快照（S24）+ 写 verification-summary + sys.exit(0 iff 26 PASS 且 S24 PASS)。
- 每 S 检查内部异常 try/except 转该 S FAIL（S09 解析失败项记 bad9o 并 continue，S10 对缺 obA/obB 项 skip 记录，
  不再让未捕获异常炸掉主程序）。
- 快照读取错误显式记录：SecurityLab 树含环境既有损坏 reparse 点（tools/binwalk/cargo-home/bin/cargo，
  os.stat WinError 1920）——收集"不可访问清单"，前后一致不算树变更但写入审计记录（不静默 continue）；
  前后清单变化 ⇒ S24 FAIL。

## 五、L-80 / L-67 证据强化
- **L-80**：compare facts=[state, recovered_len, recovered_sha256]；spec 增 `ref_sha_file: inputs/prog.ts` +
  ref_sha256；S10 对 A、B 各自断言 recovered_sha256 == sha(prog.ts)（三方逐字节全等）。
  现场：A/B recovered_len=22748、SHA bd3dc72e079111211309884238a515a7aea31e87e2015e729dd1b547f372f884 == 参考。
- **L-67 方案一（优先）**：analyzer-b 增**独立物理帧遍历**（同步字→帧头表→帧长推进，与 A 不共享代码），
  输出 codec_name/sample_rate/frame_count/contiguous；A/B frame_count=79=79、contiguous=True=True。
  ffprobe nb_read_frames=78 作为外部参考行保留，差异（解码帧 vs 物理帧/Info-Xing/尾帧）**说明保留，不强行相等**。
  方案二（B 只能 codec/sample_rate 时）：CV 范围收窄为"MP3 头字段映射的 codec/sample_rate"，帧遍历/连续性降 LR。

## 六、12 类失败探针执行要点（全部 --root 系统临时副本，history 保留全部 stdout/rc）
1 正控 expected.accepted 翻转→S08 FAIL（accepted=29/30）；2 expected.decision 改另一合法枚举→S08 FAIL；
3 负控 accepted 翻转→S11 FAIL；4 负控 decision 改错→S11 FAIL；5 删 observed accepted/decision（adapter 抛）→解析 FAIL；
6 L-80 B 输出尾部追加假 recovered_sha256 行→S10 FAIL（S20 PASS）；7 副本 memory 删 1 锚点→S03 FAIL；
8 memory-candidates 注入动态禁入值（snmp_password）→S22 FAIL，删除后干净 PASS；9 final-hashes 删项/非 64 位→S23 FAIL；
10 adapter 抛异常→对应 S FAIL 且 S24 仍执行 PASS、summary 存在、rc≠0；11 output-dir 位于 SecurityLab 内 / --root 内
→执行前 rc=3 拒绝；12 干净副本全 PASS。
S20 全程保持 PASS（每探针 mutate 后重建副本 manifest）。

## 七、陷阱（本轮真实事故，排序按出现轮次）
- **--root 副本探针静默无效**：验证器常量（spec/rule-map/audit/pre/fh/observed 规则）若硬编码主树路径，
  探针 mutate 副本文件全部空转（probe1/2 只报 S23 环境缺键，主因 S08/S11 永不触发）。修复：R6 与规则路径一律
  `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` 推导（副本里自动指向副本），主树常量只留
  SECURITYLAB/SOURCE/TOOL。
- **commonpath 拒绝漏判（normcase 只做一侧）**：`os.path.commonpath([outdir, f]) == os.path.normcase(os.path.abspath(f))`
  在 Windows 上恒不相等——commonpath 保留原大小写（C:\Users\...）而 normcase 全小写；**两侧都 normcase** 才拒绝
  （probe11b 首测 rc=1 而非 rc=3）。
- **observed 取"最后出现"用 re.findall 取 [-1]**：篡改探针在 analyzer 尾部追加假行（recovered_sha256='0'*64），
  re.search 取首行真值永不命中 ⇒ 探针空转。负控 state/status 多行同理。
- **subprocess "python" 解析不确定**：3.8 入口启动时 "python" 可能解析到 3.8（无 PIL/错误 magic）⇒ Runner 一律用
  runtime-manifest 的 hermes-venv-python311 绝对路径执行 analyzer。
- **observed decision 判定用消息前缀/全值而非非空**：L-56 负控 ttl64 输出 ascii=b'@@@@…' 非空但非 TRAINING；
  L-46 scale 的 decoded 非空（0x00-0x07）但 meta_texts=[]——非空误判 ok。判定 `startswith("TRAINING_P3_L56")` /
  `decoded == 完整消息值` 才 ok。
- **负控 method 选错使语义不存在**：L-18 high-entropy 负控挂 method b，但 analyzer-b 输出 `key=7c`（低分也输出 key），
  且 B 无 single_key 概念 ⇒ 改 method a（A 无 single_key 行→no_single_key）。
- **glob 取"最新 run"要按 mtime 排序**：多轮 closure 共用同 prefix 目录，sorted(glob) 按 run_id 随机序 ⇒ 复制到
  旧 run 的 summary（identical=False 事故）；`sort(key=os.path.getmtime, reverse=True)` 取 [0]。
- **报告必备逐字句**：教师钦定声明句（`未开始阶段4；未写项目 Memory；未写 Hermes 全局 Memory。`）必须**逐字连续**出现，
  括注插中间 ⇒ S26 子串检查 FAIL（修改后重跑才过）。
- **S23 时序死锁与解**：S23 需要 output/summary/records/probe 文件（finalize 封装产物）在 final-hashes 中且磁盘匹配，
  而这些文件来自验证器运行 ⇒ closure-1（S23 缺键 FAIL，语义项全过）→ finalize 封装 closure-1 输出 → fh 补键 →
  closure-2（26/26）→ finalize 用 closure-2 输出覆盖 → fh 同步 → 结束；报告引用最后 closure，教师复现 fh=磁盘。
- **探针长跑**：12 探针 × ~3.5min ≈ 40min，后台 + 逐条 flush + 中途落盘 probe-results.json；kill 旧版重跑（验证器中途改动
  使旧结果作废）；bash 无 job control 时并发用 Python Popen。
- **L-67 A 侧 frame 计数键**：A 输出 `frames=`，B 输出 `frame_count=`——observed/canonical 统一键 frame_count，
  A 侧 `_grab(frames=(\d+)) or _grab(frame_count=(\d+))`。

## 八、终态交付序列（本轮回放）
门禁（锁/SOURCE 双哈希/阶段2 13 项/rem-05 fh 40 项+报告+fh 自身+旧验证器+旧 spec 精确哈希/Memory 5 锚点逐项）
→ 冻结 pre（622 条）→ 状态块 `Phase 3 Remediation-6 Required` 追加 3 文件 + rem-05 报告 Superseded →
analyzer 强化（L-67B 独立帧遍历/L-80 输出已含 recovered）→ cv-claim-fact-audit.json（18 项逐项
claims/validated_scope/unvalidated_scope/A/B 实际规范事实/compare/支撑理由/候选保留与删除句）→
spec-v4 + observed-rule-map → 验证器 v6（S01-S26）→ 迭代至 r9 = 23/26（仅 S04 pre 重建前/S23/S26 终态依赖）
→ 报告终稿（逐字声明句）→ final-hashes 28 项 → pre 终稿重建 → closure-1 → finalize → fh 补键 →
closure-2/3（顺序 3.8+3.11 与并发全部 26/26 rc=0）→ finalize 覆盖 → fh 同步 → 交付摘要。
最终：CV 18 / LR 11 / Partial 1 / TG 6（门槛 CV≥18、CV+LR≥24 恰过，无空洞字段凑数）；
cv-claim-fact-audit 确认 18 项无降级需求；memory-candidates 29 条；报告不内嵌自身哈希。
