# 阶段3 教师定向纠错补训轮（Remediation-01）完整配方

> 实证：2026-09-03，36 项实验首轮后教师现场复核 → 11 项全局缺陷 + 11 项定向纠错 → `Phase 3 Remediation Completed`（R1-R20 全 PASS rc=0）。前置阶段3配方见 `phase3-micro-experiments.md`。

## 轮次结构
教师复核首轮成果后下发《阶段X教师定向纠错补训指令》：状态从 `Execution Completed` 改 `Remediation Required`；不推倒重做、不把 Tool-Gap 强转 PASS；保留首轮全部原始错误/输出/审计轨迹；修复全局证据链与终验器；定向重跑明确列表项；补工具暂存纪律；按实际证据重新分档；达门槛才 Completed。

## 门禁（含锁文件重检纪律）
- 教师现场复核可能发现 SOURCE 被编辑器占用 ⇒ 指令要求：锁文件存在就输出 `Paused — Source Still Open` 并停止，**不写任何文件**；训练者关闭后**从 G0 重新现场检查**，不得沿用暂停前判断（任务消息可能明说"不得沿用缓存结果"）。
- 诊断占用：`tasklist | grep -iE "winword|wps"` 只读确认；**绝不强杀用户编辑进程**。
- 锁消失后：SOURCE 双哈希（两次间 ZIP 结构读）+ 阶段2 冻结清单逐项现场核 + 五个 Memory 锚点 + 阶段3 首轮锚点现场算（不用报告抄值）+ 36 目录/文件数核对。
- **文件数核对会撞上外部预置**：暂停期间教师/并行会话可能已创建 `remediation-01/`（pre-remediation-files.sha256 + claim-id 映射等）。处置：盘点内容 → 现场复算清单（358/359 一致 + 1 项同秒时序竞争可解释）→ 判定为合规预置、采用为新基线并记录时序，**不得回滚或删除**。

## 教师 11 类全局缺陷模板（逐项对照修复）
1. 终验器覆盖不足（抽样/跳文件/门槛错/信布尔声明）→ 重建 R1-R20 级增强验证器。
2. **manifest 与 result.json 哈希失配**：首轮在 manifest 生成后修补过 result.json（断言如实化/格式修正）但没重建清单 ⇒ 教师现场复算抓到。修复：**登记变更时序**（不得把哈希改成现场值后声称首轮一直一致）+ 全部 manifest 统一重建。
3. 缺 README.md → 36 个从 result+知识卡生成（不新造结论）。
4. result.json 缺 `evidence_integrity`（6 字段：initial_run_pre/post_hash_recorded、historical_limitation、remediation_start_manifest、remediation_end_match、source_evidence_unchanged）→ 首轮没采集前后哈希就写 false + limitation，**禁止追溯伪造 true**。
5. `claims_tested` 空/用断言数冒充 → 用权威 claim 映射（外部预置 claim-id-final.json 须先程序化验证：36 L 全覆盖、ID 全部存在于 claim-validation 233 行）→ 写入真实 A-/B-/C-/D- ID；无对应主张写 `[]` + `no_claim_reason`。
6. result_status 非规范 → 只允许六值 `Cross-Validated / Locally Reproduced / Partially Validated / Tool-Gap / Contradicted / Blocked`；括注/复合状态移 conclusion/evidence_after；原值存 result_status_historical。
7. 纯 Tool-Gap 仍写 methods_independent=true → 无方法应为 false + method_na_reason，不伪造 analyzer/控制样本。
8. STAGED_TOOLS 空 + 首轮直接从 TOOL_SOURCE 运行 → 违规**如实披露**（"无法追溯证明首轮源工具前后不变，未发现当前损坏"）；本轮先复制最小副本再运行。
9. memory-candidates 含 Tool-Gap/未验证规则 → 只保留已验证可迁移；Tool-Gap 实验整体移出。
10. 统计范围标签与实现不一致（ones_in_64 实为 256 位）→ A/B 同范围逐位比较。
11. "36/36 断言全过"掩盖专门负控制未达标 → **功能断言/审计断言分列**（functional_assertions / audit_assertions 各自 pass/fail）；"如实报告失败"类断言只计审计，不计功能 PASS。

## 11 项定向实验通用改法（功能断言全过后才谈升级）
- **负控制必须真实改变输出**：L-82 "错误域"负控制初版不生效——简化 blob 无 AV 对，域根本不参与 HMAC ⇒ 无效负控制。升级标准 NTLMv2 blob（0x0101 + ts + CC + AV 对 domain/user + EOL）后域/用户名大小写才真实改变响应。**每条负控制跑完核对"与正确结果不同"再算通过**。
- 负控制要落到物理文件 + 实际执行输出：`negative-controls/` 放样本或 README-NC.txt + nc-runs.txt（参数级负控制也要有运行记录），否则 R9 型检查 FAIL。
- 解码评分函数陷阱（L-63）：空格假设对重复串明文失效；纯数字串（'0000'）假阳性；'A'×N 重复字符假阳性；真训练串=大写+数字+下划线混合 ⇒ 评分 = 字母/下划线占比>阈值 **且** 含大写 **且** 含数字；ascii 直读命中后禁止再报 offset 双解（互斥）。
- 断言必须匹配自身语义：写"如实 rc"却仍要求 rc=0 是自相矛盾；5600 行格式 `USER::DOM:...` split(':') 是 6 段（空段）不是 5 段。
- 诚实分级案例：L-78 高位深/色彩未验证会被指令强制降级 ⇒ 先实际合成 10-bit AVIF（av1C high_bitdepth_flag + ffprobe pix_fmt 双方法）再保留 CV；L-84 只完成 Fermat 子项 ⇒ 补 OBEX/ATT 或降 Partially；hashcat `--version` 成功 ≠ 第二验证方法（无设备 rc=-1 只作 Tool-Gap 子项）。
- 删除未测量性能推断（"20009 词约 2.8h"与实测 0.01s/3 词不相容）——要么实测要么删除。

## 工具暂存纪律（STAGED_TOOLS）
- 本轮不得直接执行 TOOL_SOURCE 任何程序/脚本/解释器；需复跑的工具先复制最小可运行副本到 `tools/staged/<项目>-remediation`。
- 记录：源路径/源大小+SHA-256/暂存路径/复制后 SHA-256/**运行后 SHA-256**/版本/命令/退出码（stage-records.json）。
- 便携性差的大型嵌入 Python（弘连 311）：可不复制不复跑，其包行为不作为通过证据，只当库来源被独立 analyzer 导入（记录路径/版本/现场哈希）。
- 系统已装/SecurityLab 自有工具不属于 TOOL_SOURCE，仍记录路径+版本+现场 SHA-256（tool-source-and-stage-manifest.sha256）。
- 只读执行不改文件（snmpv3brute stub 注入 pyshark 后运行，staged 哈希运行前后一致）。
- 工具行为与标准不符要披露：snmpv3brute 本地化跳过 RFC3414 64 轮迭代（hex 扩展直 HMAC）⇒ 对标准构造样本 Not found（0.01s/3词）——源码审计结论写进报告，A/B 标准实现结论不受影响。

## 增强终验器 R1-R20（任一 FAIL 退出码 1）
R1 锁+SOURCE 双哈希/大小/parts；R2 阶段2 冻结 13 项+Memory 5 锚点；R3 实验 ID 恰 36/四批各 9/无额外；R4 36 README + Tool-Gap 例外（tool-gap-audit + 理由）；R5 result 全字段+evidence_integrity+规范状态；R6 claims_tested 真实 ID+空表有 reason+与权威映射一致；R7 CV 有双 analyzer 文件+不 import generator/不读 truth+不相同文件+有输出；R8 LR/Partial/Tool-Gap 语义（TG 无 analyzer 不得 indep=true）；R9 非 TG 有正负控制**文件**+执行输出；R10 manifest **全条目**复算（0 解析失败/0 缺/0 未列/0 失配，禁止抽前三项）；R11 STAGED_TOOLS 清单完整+源/复制后/运行后哈希一致；R12 首轮直接运行违规已披露（不追溯伪造）；R13 11 项定向功能断言 fail=0；R14 memory-candidates 无 Tool-Gap/未验证；R15 泄漏扫描 0（样本名/载荷/密码/固定偏移/一次性哈希禁入候选正文）+Memory 哈希不变；R16 资源计数声明；R17 报告/register/results/claim map/checkpoint 统计一致；R18 CV+LR≥24 且 CV≥18（现场文件算，不信报告汇总）；R19 失败路径实测（临时假缺陷→rc=1→恢复→rc=0，记录 probe 文件）；R20 SOURCE/阶段2/Memory/TOOL_SOURCE 结束锚点一致+未开始下一阶段。

## 状态与数量重算
- 从纠错后 36 个 result.json **程序化重算**（不信首轮 22/7/6/1）。
- 缺负控制的 CV 一律不保留；没有实际第二方法的 CV 一律不保留（教师现场点名 L-63/78/80/82/83 首轮 negative_control="无"、L-82/83 缺 analyzer）。
- 通过线：36/36 登记；CV+LR≥24；CV≥18；0 未解释跳过；0 未处理 Contradicted/Blocked；R1-R20 全 PASS rc=0。达不到即 Partially Completed，不得为凑数抬高证据等级。

## 交付物清单
remediation-01/{pre-remediation-files.sha256（外部预置或自建）、issue-register.md、tool-source-and-stage-manifest.sha256、targeted-results.json、scripts/verify_stage3_remediation.py、verification-output.txt、final-hashes.json（11 项，不含自身）}；原报告顶部保留首轮+追加 Superseded/状态块；新纠错报告 `reports/<...>-phase03-remediation.md`；36 个 README/result/manifest 与汇总文件全部更新。最终复验后不得再改任何被验证文件；最终输出单摘要含 15 项（状态/门禁/11 缺陷逐项/11 定向修改前后/重算分布与 ID/CV+LR 门槛/两项失配时序/README+evidence_integrity+claim 完成度/暂存哈希/候选纠正前后/终验逐项/路径哈希/结束锚点/资源计数/未开始下一阶段声明）。
