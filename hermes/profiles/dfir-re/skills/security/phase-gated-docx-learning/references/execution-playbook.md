# Execution Playbook — 阶段门禁式 DOCX 学习（事故→教训对照）

源自 2026-08~09 SecurityLab《Misc知识总结》方案A 两轮执行（阶段1/2 + 差分重基线 + 阶段2定向纠错）的真实事故。每条均为"先踩坑→后修复"验证过的做法。

## 1. 门禁脚本模式（每阶段/纠错轮开头）
- 检查项：锁文件 `~$*.docx` 不存在；SOURCE 大小+双 SHA-256（两次之间用 zipfile 完整读一遍结构 parts/xml 字节）；阶段锚点清单逐项比对（源 inventory/extracted/image-inventory/阶段报告/data JSON/历史副本）；项目 Memory 5 文件哈希。
- 输出每项 PASS/FAIL + 实际计数；任一 FAIL 停止并报精确漂移，**不修复锚点以通过**。
- 用独立 gate 脚本（如 `scripts/gate_phase2_remediation.py`），结果留在会话记录。

## 2. 批次推进与检查点（防上下文耗尽丢进度）
- 批次行段图由 coverage-manifest 或 headings.json 生成（H1→行段范围、H2 计数、T 计数），每批读提取稿对应行段一次。
- 每批写完立即落盘：知识卡（追加段，卡头 `### KC-###`）、claim 段、memory-map 段、coverage 状态（§1 H1/§2 H2/§3 T 行状态列改 Carded + 批日志行）。
- 批末更新 stage2-checkpoint 类文件：批次进度表 + 计数对照 + 已知注意事项。上下文不足时停在批边界，绝不跨批写半张卡。
- 全部完成后跑只读 verify 脚本（数量+结构+锚点+Memory 哈希），PASS 数全过后才允许写 Completed。

## 3. 验证脚本必须检查什么（教训：首版 verify 只查数量被教师否掉）
- KC 连续唯一、17 字段齐全、主 L 编号 L-01..L-N 连续唯一。
- KC 来源定位符存在性：H1/H2 以提取稿 ⟨H1-n⟩/⟨H2-n⟩ 标记为权威；**P 以 data/paras.json 全量 id 为权威**（extracted 只显示非空段，P 有空洞——空段落）；T 以 [T-n] 标记（0 基 T-0..T-171）；IMG 以 [IMG-n] 标记。范围写法（P-a..P-b、IMG-7..IMG-13、IMG-4/IMG-5/IMG-6）需展开。
- map 恰 N 行、KC 连续、每卡一个且仅一个精确六类值（Exact Duplicate / Verified Extension Candidate / Conflict / New Candidate / Example Only / Tool Fact Candidate——类别单元格禁止括号说明，解释放匹配/差异字段）。
- claim 全部 Markdown 表格逐表头逐行列数一致；A/B/C/D ID 连续唯一；主状态属于允许状态集；当前状态列无历史词（Cross-Validated/Locally Reproduced 只许在"旧草稿状态"列）。
- conflict-register：检查范围写明 B01-B11 等全批；Active Conflicts 数量与 map Conflict 卡数、claim Conflict-Pending 状态数三方一致。
- coverage 无"其余批次未开始"类过时句；旧报告已标 Superseded；规范报告/纠错报告存在。

## 4. 事故 → 教训对照

| 事故 | 教训 |
|---|---|
| image-inventory 13 个图片哈希全是占位值（6 个不足 64 位） | 占位零容忍；哈希现场重算，ZIP 部件/images 副本/登记三方一致 |
| coverage H1/H2/T 状态更新正则组号错（group(3) vs group(8)）→ 0 更新且脚本没报 | 行级字符串处理比复杂正则稳；替换后必须计数验证 |
| map 批段替换"print OK"但锚点未匹配 → B04/B05 段静默丢失 | replace 前断言旧串在；replace 后读盘复核；锚点占位符只留一个 |
| 表格 T 编号 1 基假设 vs 实际 T-0 起（172 张 = T-0..T-171） | 先读文件确认真实编号起点再映射，勿假设 1 基 |
| 提取稿 P 编号有空洞 → 定位符校验误报 FAIL | P 存在性以 paras.json 全量编号（连续全集 0..max）为权威 |
| A-114 主张含 `SC\|\|Blob` 撑破表格（列数 9 vs 表头 7） | 表内逻辑表达式改写 concat(SC, Blob)；列审计逐表头 |
| 报告内嵌自身 SHA-256 → 写一次变一次永不收敛 | 自引用哈希不内嵌；注明"终值以交付消息为准"或冻结后外层给 |
| claim B/C 编号跨批重复（早期脚本编号失控） | 主张 ID 全表重编号时：存旧→新映射 JSON + 正文引用迭代替换到收敛（链式 A-17→A-19→A-21）+ 终检 0 残留 |
| A-10/A-25/B-20 一行捆绑多子主张、证据等级不同 | 拆原子行；拆分说明规范为"（原子拆分，映射见 mapping.json）"防二次误替换 |
| guide-2 只读"索引+抽样" → 9 张卡分类错误（点名未覆盖） | 分类判定前全文读取参考材料；点名级（出现考点名/工具名）= Verified Extension 基础；标题同≠Exact；相邻≠Verified |
| conflict-register 检查范围停在 B05、汇总写 B04，与报告声称 B01-B11 矛盾 | 范围/汇总随批推进即时更新；纠错轮按全批重写并逐项复核 CF |
| 旧报告冲突段声称含"010 Editor 菜单名"而实际 CF 无此项 | 报告描述必须与实际文件内容一致；纠错后按实际重写并标 Superseded |
| 并行执行实例修改同一文件（extracted/coverage/source-inventory） | patch 前先重读磁盘；只做最小定点修复；并行实例合规成果保留、其 §8 原文保真入附录并署名 |

## 5. 纠错轮（remediation）流程要点
- 教师指令 = 已确认纠错项清单 + 全量复核要求 + 新终验脚本要求。旧报告顶部追加 `Superseded by Phase 2 Remediation` 标记（含新报告链接），原内容一字不删。
- 按指令路径新建权威报告（如 phase02-knowledge-mapping.md）+ 纠错报告（phase02-remediation.md），逐项写"修改前/修改后"。
- 证据落盘：audit JSON（逐卡判定）、claim-id-mapping JSON、final-hashes JSON。
- 修复顺序建议：锚点门禁 → 状态置 Remediation Required → 定点修复（表格转义/来源错/位置错/过时句）→ 全量读取参考材料 → 分类修正同步（knowledge-cards 关系字段/map/claim/两份报告）→ conflict 重构 → claim 拆分重编号 → 新 verify 脚本全绿 → 报告冻结（哈希表填完后再改报告会使哈希变——最后填或注明外层给）。
- 终验 48/48 类脚本全 PASS 才写 `Phase 2 Remediation Completed`；否则 Partially Completed + 精确失败项。
