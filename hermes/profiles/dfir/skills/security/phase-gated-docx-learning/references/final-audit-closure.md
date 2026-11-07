# 最终审计闭环轮配方（Final Audit Remediation / Closure）

来源：SecurityLab 方案A 阶段2 教师"最终审计闭环纠正指令"实跑（2026-09-02）。教师对已交的 Remediation Completed 交付做**现场只读复核**后可能再发一轮闭环指令——知识内容主体保留，但审计闭环缺口必须定点修复。同型指令可能出现在阶段3/4 之后。

## 一、开始门禁（任一 FAIL 立即停止并报 `Phase 2 Final Audit Gate Failed`）
1. Office/WPS 锁文件 `~$*.docx` 不存在。
2. SOURCE_DOCX 连续两次大小 + 完整 SHA-256，两次之间完整读取 DOCX ZIP 结构；两次必须一致且等于指令给的锚点。
3. **先原样运行当前验证器并保存输出**——应为全 PASS；不是则停止。
4. 指令给出的当前阶段锚点逐项核对（含上一轮产物哈希——注意指令中的值取自冻结后的文件，若你上轮在报告中登记过自己的哈希请确认与指令一致）。
5. 五个项目 Memory 锚点（含 ctf-misc-guide-2.md 大小+哈希）。
6. 阶段1 只读锚点由现有验证器覆盖。

## 二、状态机（本轮的完整链条）
`Phase N Remediation Required → Remediation Completed（历史自评）→（教师复核指令到达）Phase N Final Audit Remediation Required → 全条件满足才 Phase N Final Audit Closed`
- 置 Required 时：checkpoint 与两份报告的当前状态行同步更新，**保留此前 Completed 为历史自评，不删除纠错证据**。
- Closed 八条件：①源+只读锚点稳定；②逐卡记录完整且与 map 一致；③53/32 等分类不变且有逐卡证据；④强化验证器全部 PASS；⑤失败路径实测非零退出码（安全临时副本/真实失败运行，不破坏正式文件）；⑥最终哈希清单与现场逐项一致；⑦五个 Memory 文件结束哈希=开始；⑧未开始下一阶段、未写 Memory。
- 任一失败 ⇒ 输出 `Partially Completed` + **精确失败项清单**；**增强验证器查出禁改文件（知识卡/claim/conflict/coverage/Memory/旧报告等）真实缺陷时不得自行修复**——状态保持 Partially Completed，等训练者决定。绝不进入下一阶段。

## 三、增强验证器（E1–E13；检查数自然增长，不凑固定数字；每项输出 PASS/FAIL+实际计数+失败原因+总数）
- **E1/退出码**：任一 FAIL ⇒ `sys.exit(1)`；全 PASS ⇒ `sys.exit(0)`。实测失败路径返回非零（真实失败运行即可作为失败路径测试）。
- **E2 17 字段严格检查**：每卡每字段"恰一次"——锚定行首正则并允许括注变体（`- 决策步骤（逐陷阱）：` 合法；模式 `- 决策步骤(?:（[^）]*）)?[：:]`）。0 次或缺 Knowledge ID 行或 ≥2 次均 FAIL。字段名：Knowledge ID/能力域与题型/来源定位符/知识类型/触发信号/最小证据/决策步骤/输入输出中间结果/适用条件/不适用条件/常见误判与替代解释/失败表现与排障/安全边界/独立验证方案（阶段3计划 L-xx）/与 P1-P48 关系/当前证据等级/置信度与待验证事项。
- **E3 主计划编号**：从权威行 `- 独立验证方案（阶段3计划 L-xx）：` 解析（勿取正文首个 L-xx），断言 L-01..L-85 连续唯一；依赖/复用编号不得当主编号。
- **E4 audit JSON**：guide_card_ids 82 个唯一（现场解析）；playbook_ids=P1..P48；card_reviews 85 条 KC 连续唯一；逐卡 category 与 map 行一致；Verified 每条须有 ≥1 既有引用 + ≥1 matching field + ≥1 difference field；New 每条须有 difference fields + "为何无字段级基线"依据（无引用时须有 no_field_basis_note）；final_counts 六类精确；逐卡记录无 64 位样本哈希/flag/一次性值。
- **E5 反向来源覆盖**：展开 85 卡来源定位符范围（支持 `..` 范围与 `IMG-a/IMG-b` 斜杠），并集 ⊇ H1-1..81 / H2-1..430 / T-0..171 / IMG-1..13。**真实事故**：H2-5（P-77..P-82 段落）无任何 KC 引用但 coverage §2 标 Carded → 唯一 FAIL → Partially Completed（涉及禁改文件，上报）。
- **E6 coverage 表唯一性**：H1 恰 81 个不同 ID=1..81；H2 恰 430=1..430；T 恰 172=0..171；每 T 行目标 KC ∈ KC-001..085；重复 ID/缺号/无效 KC/字符串凑数均 FAIL。coverage §3 T 行形如 `| H1-x | T-n | rx c | v | Included（…）→ Carded（并入 KC-00x） |`。
- **E7 IMG 权威映射**：IMG-1→KC-003、IMG-2→KC-024、IMG-3→KC-035、IMG-4/5/6→KC-058、IMG-7..13→KC-074；13 个 ID 各恰一次于权威归属集合；owner 卡内引用须含该 IMG（卡内支持 `IMG-7..IMG-13` 与 `IMG-4/IMG-5/IMG-6` 两种写法，解析时都展开）。
- **E8 跨文件统计一致性**：checkpoint/规范报告/纠错报告须程序化命中同一组统计事实（85、233、H1 81、H2 430、T 172、IMG 13、Verified Extension Candidate 53、New Candidate 32、Active Conflict 0、Conflict-Pending 0），且六文件（+map/coverage/claim）无矛盾计数（54/31/52/86 等）。正则间距 `[^0-9]{0,12}` 以免"状态主张 = 0"式长间隔误报。
- **E9 资源与状态声明**：三文件须含 下载 0/联网 0/安装 0/升级 0/实验 0/项目 Memory 写入 0/全局 Memory 写入 0/P49 新增 0 + "阶段3 未开始"明确表述 + 只读审计与功能测试分开表述（verify 运行是只读审计，不是实验/测试）。
- **E10 阶段3 防越界**：工作目录/reports 无 phase03/Phase 3/L-xx 执行产物文件名；Memory 目录 .md 集合=期望清单（含 PROJECT_MEMORY_POLICY.md）。
- **E11 最终哈希清单**：读 final-hashes.json 逐项重算 size+SHA-256 比较；缺文件/旧哈希/大小不符 FAIL；清单不得含自身条目。
- **E12 报告质量**：map 头部无"已回读索引/只读索引/索引+抽样"旧表述；纠错报告不得登记他报告旧哈希（如旧 8,634B/334bd7ee…）也不得残留破损残句；旧报告保留 Superseded；三文件当前状态词**单一一致**（正文勿写"将来会变 Closed"之类未来式——正则会把未来式当第二状态）。
- **E13**：逐项 PASS/FAIL 输出，不只输出总数。

## 四、audit JSON 机器可审计结构（85 条逐卡）
顶层键：`guide2_full_read{lines,bytes,sha256,card_count}`、`guide_card_ids[82]`（正则 `\*\*Knowledge ID\*\*[：: ]*([A-Z0-9\-]+)` 现场解析）、`playbook_ids`、`card_reviews[85]`、`classification_changes`（历史 9 项保留）、`final_counts`、`consistency_assertions`。
card_reviews 每条：`kc_id / source_locator / closest_existing_refs[{type:P|guide,id}] / no_field_basis_note / matching_fields / difference_fields / category / decision_basis / stage3_plan_id / map_h1`。
要点：
- matching/difference 文本直接取自 map 行权威列（map 是此前人工逐行核对的产物），不二次编造；map 口语引用（"guide BMP 卡"）需 speech_map 映射为规范卡 ID（映射前用关键词在 guide 全文检索确认，如 wbStego→MISC-STEG-IMG-BMP-001）。
- 点名级匹配（guide 仅点名主题如 Arnold/拼图题，map 匹配列写"无"）→ matching_fields 填"点名级（触发信号级匹配），无字段细节"，否则 Verified 的"至少一个 matching field"断言 FAIL。
- 行数口径：教师给的 guide 行数按 `\n` 计数（1376）；`split("\n")` 因尾随空串得 1377——记录并注明。

## 五、报告/哈希冻结顺序（防自引用不收敛）
1. 先完成全部正文修正（map 头部、audit JSON、验证器、两份报告正文、checkpoint 状态）。
2. 跑增强验证器**预终验**；FAIL 即停止，不生成 Completed。
3. 预终验通过后：纠错报告 §八 登记"已冻结的其他文件"大小+SHA-256；**本报告自身与 final-hashes.json 不内嵌自身哈希**（自引用永不收敛）。
4. 删除破损重复残句，改为单一可读自引用说明——描述时不要引用残句原文，否则 E12 检查再次命中。
5. 冻结所有允许修改文件。
6. **最后**重建 final-hashes.json：每条含绝对路径/size/完整 64 位 SHA-256，**排除该 JSON 自身**。
7. 重建后跑最终复验；复验后禁止再改任何文件。
8. final-hashes.json 自身的大小/SHA-256 只在最终回复中给出。
