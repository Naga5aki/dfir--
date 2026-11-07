# 阶段3 Remediation-5：语义验证与严格只读闭环轮配方

实证：2026-09-04，S01-S24 × 6 次正式运行全部 24/24 PASS rc=0（顺序双入口 3.8.6/3.11.15 + 并发双入口 + REL2 最终只读复现双入口），五类失败探针命中，报告 19,744 B。

## 教师点名的四类 rem-04 缺陷（报告 §一 必须如实记录，不改写）
1. 验证器正式模式写 `remediation-04\execution-records.json` 与 `verification-summary.json`，S24 未比较正式树前后状态 ⇒ "S24 验证器只读"不成立；3.8/3.11 并行争用同一文件触发 PermissionError。教师复验现场 mtime 未覆盖=教师没改正式结果，如实承认。
2. S08 只查 rc∈allowed_exit_codes + 无异常关键词，不读 expected_positive ⇒ 错误结论 rc=0 也过。
3. S10 `both_success` = "两边输出非 False/None/0"，不是同一事实相等。L-38/46/56/58/63/66/67/69/78 九项旧映射必须纠正或降级。
4. S12 负控制循环体 `pass` ⇒ 负控 Traceback/超时/UnicodeDecodeError 不进 S12。

## 门禁（§三）
锁 ABSENT（出现即暂停）→ SOURCE 双哈希（哈希一→完整 ZIP parts 读取→哈希二）2,869,147 B/31 parts/`f7680839…41c21` → 阶段2 13 项 → Memory 5 锚点 → **rem-04 final-hashes 现场核对**（状态块追加致报告条目变 ⇒ 更新+note，pre 冻结保留为漂移证据）→ rem-04 报告现场 12,048 B/`f7fdcc7d…71973` → 36 manifest → 冻结 pre（全口径 579 条）→ 状态块追加 5 文件 + rem-04 报告 Superseded 标记（不删原报告/输出）→ 任一无关漂移即停不自修。

## 严格只读验证器架构（§四）
- 必填 `--output-dir <绝对路径>`；位于 SecurityLab/SOURCE 目录/`D:\CTF_Misc_Tools` 内部 ⇒ **执行实验前 rc=3 拒绝**（探针 5a 实测）；须在系统临时目录下；每运行生成 run_id（uuid4）子目录。
- 验证器对 SecurityLab 零写：无写模式 open/json.dump/write_text/makedirs/copy/remove/rename；execution-records/summary/临时 analyzer 输出全写 output-dir。
- 每实验/方法/控制唯一临时目录（uuid 后缀）；禁固定实验 ID 与 Python `hash()` 命名（hash() 受 PYTHONHASHSEED 影响且跨进程不稳定）。
- 两验证器实例可同时运行：不同 output-dir、互不删除/覆盖/读取对方目录。bash 后台 `( … ) &` 子 shell 语法在此环境报错 ⇒ 用 Python subprocess.Popen 双进程并发（实证双 24/24、0 PermissionError）。
- **全树快照**：walk SecurityLab → {规范化 rel: size/SHA-256/mtime_ns} + 文件总数；前后逐项相同，任一新增/删除/内容/mtime 变化 ⇒ S24 FAIL。只比 36 manifest 不算；"写完相同内容"不算。损坏链接 os.stat OSError（WinError 1920）⇒ 前后一致跳过。运行期间外部并发写入 ⇒ 环境冲突停止不归咎实验。
- **封装分离**：`finalize-remediation-05.py` 独立复制临时目录规范输出入轮目录（verification-output-*.txt / summary / execution-records），记录命令/来源目标 SHA/时间到 finalize-record.json。

## spec-v3 规范结果对象（§五）
每正/负控制产生：`{experiment_id, method, control_id, accepted(bool), decision(预列枚举), canonical_facts{类型化}, artifact_hashes{}, errors[]}`。canonical_facts 不得塞整段 stdout；二进制=size+SHA-256+Base64；解析失败/字段缺失/重复字段/类型不符 FAIL。展示 stdout 可保留但不替代规范对象。adapter 只解析 analyzer 现场输出，禁读 truth/generator；未知映射值拒绝（L-38 class 非 1/2、pix_fmt 非白名单 → KeyError → S08/S09/S11 FAIL）。

## S08/S09 语义验证（§六）
30 项 A + 18 CV B：实际执行 + rc∈允许值 + accepted 与 expected_positive.accepted 一致 + decision 一致 + canonical_facts 每字段存在/类型/值相等 + artifact 哈希一致 + errors 空 + 无异常。**B 侧只断言 compare.facts 子集**（B 不发 A 独有字段：L-49 ne_64、L-66 checksum_ok_lines——spec expected 全字段只对 A）。

## S10 比较类型矩阵（§七，无 both_success）
- exact_equal / set_equal（无序集合）/ artifact_hash_equal / mapped_equal（显式有限映射表，未知 code 拒绝）。
- 21→18 CV 处置（九项旧 both_success）：
  | L | 保/降 | 共同核心规范字段 | A / B 值 |
  |---|---|---|---|
  | L-38 | 保 CV | elf_class_bits,endianness,machine（mapped：class 2→64/endian 1→little/machine 62→x86-64） | 映射值 / file+readelf 直读 |
  | L-46 | **降 LR** | B 只有 chunks_ok（无消息恢复） | — |
  | L-56 | **降 LR** | B 只有 ttl_unique 无序统计 | — |
  | L-58 | **降 LR** | B 只有 sync_headers=3 | — |
  | L-63 | **降 LR** | B 只有 low8_all_printable | — |
  | L-66 | 保 CV | coords set_equal（3 点集合相等；checksum_ok_lines 为 A 独有主张） | 同坐标集合 |
  | L-67 | 保 CV | codec_name, sample_rate（A 新增规范化输出行）；frame 79 vs ffprobe 78 差 1 ⇒ 拆分记录不进入共同字段 | mp3/44100 = mp3/44100 |
  | L-69 | 保 CV | container_format=vmdk（描述符解析 / qemu-img 识别） | vmdk = vmdk |
  | L-78 | 保 CV | bit_depth（A av1C 位域→10 输出行；B pix_fmt yuv420p10le→白名单映射 10） | 10 = 10 |
  - 另：L-32 由 LR 升 CV（A/B 独立实现输出共同 co_name=`<module>`/magic=a70d0d0a）。
- 终态：**CV 18 / LR 11 / Partial 1（L-06）/ Tool-Gap 6**；CV+LR=29≥24、CV=18≥18（恰达标线，无 both_success/空洞字段凑数）。降级致不达标只能 `Partially Completed`。

## S11 负控制断言（§八）
精确比较 rc/accepted/decision/canonical_facts（JSON 类型值）；`_not_contains`/差异哈希只作补充；禁字符串 key=value 搜索代替类型比较。负控若返回正控 accepted=true/decision=success 必须 S11 捕获（探针 3 实证：neg 样本换阳性 → seq_strict_continuous=False 断言失败）。

## S12 all_runs（§九）
统一列表：30 正 A + 18 CV 正 B + 全部负控制（A/B）+ L-32 错误分支（rc 1/2/3）+ staged + 辅助工具 = 84 条/入口实证。每 run 查：timeout/启动失败/未预期 rc/异常关键词（Traceback/Exception/UnicodeDecodeError/PermissionError/reader-thread）/结果对象解析异常/缺输出/非 UTF-8 字节受控保存。原 `for negative_control: pass` 删除；summary 报 all_runs 总数、异常 0。

## 冻结→复现→封装→final-hashes 时序（关键）
1. 全部正式修改定稿（analyzer/状态文件/register/data/checkpoint/报告）→ 重建 36 manifest（469 条）→ 重建 pre-manifest（**同一全口径路径集** 579 条）。
2. 更新 final-hashes（S23 在复现时核对 fh vs 磁盘——finalize 脚本等改动后必须先同步 fh 再复现，否则 S23 FAIL）。
3. 最终只读复现（双入口顺序；树内零写 ⇒ S24 前后快照一致）。
4. finalize 封装（复制 temp 输出入轮目录 + finalize-record）。
5. 重建合并 verification-summary.json / execution-records.json（双入口节 + identical 断言）→ 再同步 final-hashes。
报告只引用该次只读复现（§4.3）；报告定稿后不再改树。

## 五类失败探针（§十二，history 保留全部尝试）
1. 错误正控制值：L-03 A width→999 ⇒ **S08 FAIL**（probe1 首轮 rc=0：正则 `width=(\d+)` 未命中 print 模板 `width={w}`——mutation 未生效；修正 `width={w+1}` 后 probe1b rc=1 命中。**改前先看目标行真实格式**）。S20 PASS。
2. A/B 语义不等但均成功：L-03 B width+1 ⇒ **S10 FAIL**（S09 同步捕获）。
3. 负控制伪成功：neg 样本换阳性 ⇒ **S11 FAIL**。S20 PASS（同步临时 manifest）。
4. 负控制 traceback：L-66 neg 路径 raise ⇒ **S12 FAIL**（S11 rc 同步捕获）。
5. 只读：output-dir 指 SecurityLab 内 ⇒ 执行前 **rc=3**；干净 3.8/3.11 顺序与并发全 24/24；全树快照一致。
探针均在完整系统临时副本（--root 副本：experiments + remediation-05 全拷）执行，mutation 后重建副本 manifest。

## adapter/canonical 实现坑（现场事故）
- `int(_grab(...))` 对负控输出（无该字段行）抛 NoneType ⇒ 先判 None 再 int；拒绝类负控（NOT_ELF rc=1 等）expected.canonical_facts={} 且 adapter 返回缺失键不抛。
- 负控专有断言字段在 adapter 里"有则提取"：L-07 crc_mismatch、L-67 contiguous、L-69 container（=unknown）、L-11 unrar_t_rc、L-46 meta_texts、L-58 frames、L-59 kb_chars/classes、L-63 candidates、L-78 has_meta。
- spec expected 值与输出变量名逐字对齐（键=真实前缀如 seq_strict_continuous，非缩写）。
- L-01 hextext 输出=原始 2 字节 ⇒ bytes_sha 对 out_b 原样算（对 backslashreplace 文本再 latin1 编码是错值）；L-01 无 \r\n 尾（buffer.write）。
- L-32 co_name 输出 `<module>` ⇒ pattern `\S+`；L-72 B 变量名 `b_first32`；`_grab` 返回 str 需 lower/类型转换统一。
- execute_code 沙箱 python 无 PIL（L-72 B ModuleNotFoundError）；hermes venv python 有 ⇒ 一切运行用 runtime-manifest 绝对路径（hermes-venv-python311）。
- 断言源遍历排除 exit_codes/accepted/decision/key_fields/_* 键自身（曾把 key_fields={} 当字段断言）。

## 门禁/状态附加
- rem-04 报告加 `Superseded by Phase 3 Remediation-5` 标记于标题后，原报告与输出原样保留。
- 七处同步：README/result.md/result.json（36 实验）+ data/experiment-results.json + claim-experiment-map.json + memory-candidates.json + experiment-register.md + checkpoint（状态调整 L-32→CV、L-46/56/58/63→LR 一次做完）。
- 资源计数全 0 申报口径同前；未开始阶段4、不写项目/全局 Memory；完成后停止等训练者提交。

## 交付物清单（§十四，均落 remediation-05/）
runtime-manifest-v2.json（runtimes{system-python38: 3.8.6 magic 550d0d0a；hermes-venv-python311: 3.11.15 magic a70d0d0a}，含 path/version/arch/size/sha256/scope）、verification-spec-v3.json（30 项）、scripts/verify_stage3_remediation_05.py（--output-dir 必填 + --root 探针副本）、scripts/finalize-remediation-05.py、verification-output-python38/311.txt、verification-output-concurrent-python38/311.txt、verification-summary.json（合并双入口 identical）、execution-records.json（双入口各 84 条）、failure-probe-history.txt（含首次失败）、failure-probe-final.txt、pre-remediation-files.sha256（579 条）、final-hashes.json（40 项，不含自身；自身哈希只放交付消息）、finalize-record.json、probe-results.json。
