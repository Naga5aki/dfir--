# 阶段3 良性微型实验轮 — 完整配方（36/36 实证，2026-09-02）

来源：SecurityLab 方案A Misc 知识总结阶段3（36 项实验，KC-001..085 的 L-xx 计划落地）。本文件是执行配方；教师指令为准时以指令为最高优先级。

## 1. 开始门禁（顺序敏感）
1. 锁文件 `~$*.docx` 不存在。
2. SOURCE_DOCX 双 SHA-256（两次哈希之间完成一次 zipfile 结构读取，记录 parts 数）。
3. **原样运行阶段2验证器并存档 —— 必须在创建 PHASE3 目录之前**（阶段2验证器 E10 检查"工作目录无 phase3 文件"，目录一旦存在必然 FAIL；这是设计冲突而非漂移，见 §6）。
4. 阶段1/阶段2/Memory 锚点核对；PHASE3 不存在则新建。
5. 门禁输出落盘 `PHASE3\gate-output.txt`（含 76/76 存档）。

## 2. 工具盘点（零下载优先级链）
SecurityLab `tools/` 已验证副本 → 外部工具池 `D:\CTF_Misc_Tools\` 现有副本 → 系统已装（WinRAR 7.22、ffmpeg/ffprobe WinGet、WSL Ubuntu file/readelf/strings/objdump、Git mingw64 openssl）→ 弘连取证 GoldenEyesV4 `Python311\python.exe` 副本（自带 pycryptodome→MD4、pyzbar 0.1.8+libzbar DLL——本 venv 缺这些时的替代源）→ 自写只读解析器。
- 工具健康检查：0 字节 exe = 损坏占位；PyInstaller GUI（CTF-NetA/PaperBack/010 Editor）无头不可交互 → Tool-Gap 注明 GUI-only；aircrack-ng 包可能只有 GUI+DLL 而核心 exe 缺失；hashcat 无 OpenCL/CPU 设备时启动即停（rc=-1，--force 也无效）→ 记"工具存在但后端缺"。
- qemu-img 2.3.0 的 `convert -f vpc -O raw` 输出全零（工具缺陷）→ 容器往返改用 VMDK monolithicFlat extent 逐字节比较。
- 记录每工具 path/version/sha 进 tool-matrix.md 与 result.json `tool_path_version_sha` 字段。

## 3. 每实验 10 文件协议（36 项一致）
```
experiments/L-xx/
  generator.py          # 离线合成样本 + 写 truth.json（样本全离线：Python/Pillow/ffmpeg/工具自带公开测试文件）
  analyzer-a.py         # 方法 A（自写解析/算法）
  analyzer-b.py         # 方法 B（独立实现或独立工具；不得 import generator、不得读 truth；两方法不共享核心函数）
  inputs/               # 正控制样本
  negative-controls/    # 负控制样本（负控制不得产生消息/误报）
  derived/              # 中间/恢复产物
  outputs/run-output.txt# analyzer 真实 stdout 存档
  manifest.sha256       # 目录全量哈希（绝对路径/大小/SHA-256）
  result.json           # 25 字段 + assertions（见 §4）
  result.md             # 人类可读版
```
- 正/负控制是硬要求：Cross-Validated/Locally Reproduced 实验必须同时有"正控制能解出"与"负控制不解出"证据。
- **result.json 必须由 analyzer 真实 stdout 驱动**：先运行再按输出填断言。L-58 事故：analyzer 文件尚未写入就生成 result.json（断言按意图记 True）→ 假 PASS；发现后删除产物、写入 analyzer、真实运行重建。

## 4. result.json 25 字段 schema
`experiment_id, kc_id, title, category_before, source_locator, claims_tested, hypothesis, input_files{size,sha256}, exact_commands, tool_path_version_sha, method_a, method_b, methods_independent(bool), positive_control, negative_control, expected, actual, assertions[[name,bool]...], observation, inference, alternative_explanations, conclusion, applicability, non_applicability, failure_modes, safety_boundary, result_status, evidence_level_before, evidence_level_after, unresolved_items, memory_candidate`
（memory_candidate 供阶段4 Memory 写入门禁：触发/最小证据/步骤/停止/替代/边界/验证 ID，本阶段只落盘不写 Memory。）

## 5. 状态分级（如实降级）
- **Cross-Validated**：双独立方法一致 + 正控制 + 负控制（或数学层 A/B + OpenSSL 等三方）。
- **Locally Reproduced**：单一实现自洽 + 负控制，但缺第二工具/真实样本（如实列 unresolved）。
- **Tool-Gap**：无真实工具/格式规范/样本 → 不猜造（PaperBack、WPA 802.11 样本、crackle、七码制中多数）。
- **Partially Validated**：主体成立但明确子项缺口（如 APNG seq 单调性检查未实现、经 CRC 路径间接检出）。

## 6. 阶段2验证器 E10 × PHASE3 结构性冲突的处置
E10 检查"工作目录下无 phase3/实验结果文件"，其设计时点早于阶段3 指令钦定 PHASE3=WORK\phase3。因此：
- 门禁时刻（创建前）76/76 存档 = 阶段2 完整性的权威记录；
- 此后不再把阶段2验证器全量当门禁（E10 必 FAIL 属预期）；
- 报告 §一/§九 显式披露：E10 意图（无 L-xx 结果混入 WORK 顶层、无 Phase 3 Completed 报告驻留 WORK、无 Memory 持久化）由终验器 V8（stray=[]、顶层无杂物）+ V9（阶段2 final-hashes 13 项现场一致）双重满足。

## 7. 汇总产物（PHASE3 下）
`experiment-register.md`（36 行状态表）、`tool-matrix.md`（采用/缺口两表）、`checkpoints/batch-a..d.md` + `stage3-checkpoint.md`（每批开始/结束复核 SOURCE/Memory/阶段2 锚点）、`data/experiment-results.json`、`data/memory-candidates.json`、`data/claim-experiment-map.json`、`scripts/verify_stage3.py`、阶段3报告于 `reports/`（不内嵌自哈希）。

## 8. 终验器 verify_stage3.py（V1-V12，FAIL 非零退出码）
V1 锁文件不存在 / V2 SOURCE 双哈希=锚点(parts) / V3 36 目录+result.json 全字段+断言全过 / V4 36 manifest 抽样哈希现场一致 / V5 analyzer 无网络 import 且不依赖 generator/truth / V6 状态分布（CV+LR ≥ 半数，Tool-Gap 如实）/ V7 双方法独立声明+正/负控制 / V8 无越界（stray=[]、PHASE3 顶层无杂物——注意检查器遍历 WORK 顶层时须排除 PHASE3 目录本身）/ V9 阶段2 final-hashes 现场一致（该 JSON 是 dict：文件名 → {path,size,sha256}）/ V10 五个 Memory 锚点一致 / V11 gate 记录+资源声明 / V12 checkpoint 状态行恰一。报告写入后**复跑一次**确认仍全 PASS。

## 9. 批次纪律与报告
- 四批 × 9 连续执行；批次间只落内部检查点，不等待教师回复；上下文不足在批边界停。
- 每批检查点含状态分布表 + 批次汇总 + 边界遵守 + 锚点复核结果。
- 报告结构：§一 门禁（含 E10 结构性说明）→ §二 执行 → §三 结果总览 → §四 工具盘点/Tool-Gap 总登记 → §五 可复用结论 → §六 自身缺陷审计（修复清单，透明）→ §七 资源计数 → §八 与阶段2 衔接 → §九 终验 → §十 交付物哈希（文件不内嵌自哈希）→ §十一 状态与待办。
- 计数：下载/联网/安装/升级/实验/项目 Memory/全局 Memory/P 编号改动；结束=开始。
