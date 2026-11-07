# 阶段3 Remediation-03（最终证据闭环）与 Remediation-04（运行时与真实交叉验证）配方

实证轮次：rem-03 2026-09-03（24/24，后由教师 rem-04 指出 22/24@py3.8 等 7 项现场失败并 Superseded）；rem-04 2026-09-03（双入口 24/24、五类探针命中）。
本文件是 SKILL.md 正文"阶段3 最终证据闭环/运行时交叉验证"陷阱的完整配方与逐项出处。

## Rem-03：验证器从"结构审计"升级为"真实执行验证"
- 核心：S 系列验证器不再读 result.json 字段声明，而是**复制实验到系统临时目录真实运行 analyzer**，比较 stdout/rc 与 verification-spec 期望；正式树只读（验证器自身运行前后 manifest 哈希不变 = S 只读检查项）。
- 每项非 Tool-Gap 实验在 spec 里有：analyzer 入口 / 正控制命令与期望 / 负控制命令与期望拒绝 / expect / 比较规则。
- 全部正控制 A + CV 的 B + 负控制全量真实运行；报告写"24/24 PASS"必须恰好 24 项检查且每一项都在跑（禁止"跳过即 PASS"虚增计数；rem-03 曾把 rem-02 的 18/18 与 16/16 两种计数都写进一份报告被教师点名）。
- 协议锚定：L-81 内置 RFC 3414 App.A.2-A.3 四固定向量（maplesyrup 等）期望值 A/B 双实现一致命中；真实报文 msg 模式由 staged snmpv3brute 正（snmp_password/SHA FOUND）/负（3 词 NOT-FOUND）闭环。
- BER 精确定位清零 msgAuthenticationParameters（12B）而非字符串 replace；BER 解析偏移 5 连坑：定位偏移含 tag 时应指向值起点；`rd()` 返回"值起点"被调用方当下个 TLV 起点（错位侥幸命中）；顶层 SEQUENCE 是容器（子 TLV 从内容起点读，非 after）；USM 容器同理；循环边界须 `q < uvs+uvl`。A/B 独立实现均修正后闭环才算数。
- L-80 乱序真恢复：判定三态 COMPLETE / REORDER_RECOVERED（同 PID 相邻交换修复）/ INCOMPLETE（真缺失）；**跨 PID 交换 = AMBIGUOUS**（必断同 PID 子序列、不可相邻修复）；断点缺失值若出现在序列别处（移位型）→ AMBIGUOUS，真缺失 → INCOMPLETE；恢复完整性 = 恢复流与源字节 SHA-256 全等（22748 B），ffprobe 可解析≠完整。
- L-83 会话重组：会话=双向四元组配对；每方向 TCP seq 线性化（分段自动拼接）；重传=同 seq 同字节去重；overlap=同 seq 异内容异常（不判可靠会话）；同内容不同 seq=合法段不误删；token 按帧到达序归属起始段收集。
- L-84 ATT 空值（empty）→ 结构有效非协议非法（空值改为边界控制实验，不再当非法）；OBEX PUT 单包多 header 聚合如实声明（多包重组 unresolved 时不得虚报）。
- 负控制设计原则：每负控制跑完核对"输出与正确路径不同且差异来自被验证机制"；物理文件与执行记录两者都要。

## Rem-04：运行时显式化 + 机器可审计 + 双入口验证
教师 rem-04 现场点出的 rem-03 失败（报告 §一 必须承认并保留，不改写）：
1. rem-03 验证器由系统 Python 3.8.6 启动 22/24（L-32 .pyc 为 3.11 magic）——隐式 sys.executable 依赖启动解释器；
2. 输出开头有 UnicodeDecodeError 线程异常仍判 24/24（reader-thread 错误被吞）；
3. 21 个 CV 中 14 项用 a_contains，旧 S09 对 a_contains 不运行 B 却报"A/B 一致"；
4. spec 有 6 项无负控制、7 项 reject_expect=null；
5. 失败探针 probe2 首次 rc=0/24/24（负控制假 PASS 绕过）被保留在 output 里，报告只写修正后结果；
6. rem-03 交付摘要的报告哈希与现场值不一致（前缀后手拼错误）——现场值以 final-hashes.json 为准。

### runtime-manifest 协议
- 现场核实每个解释器绝对路径、`--version`、arch、pyc magic（importlib.util.MAGIC_NUMBER 的 hex：3.8.6=`550d0d0a`、3.11.15=`a70d0d0a`）、解释器文件 SHA-256；类别 system runtime / Hermes runtime。
- verification-spec-v2 每项带 `runtime_id`；执行器只从 runtime-manifest 解析绝对路径启动子进程，**禁用 sys.executable 隐式替代**。
- 验证器本身必须能由两个入口启动且结果一致：正式树两次运行（3.8 与 3.11）都恰好 24/24 rc=0；summary 记 identical=True（允许 S15 行版本注记差异）；L-32 由 3.8 入口启动时仍由 manifest 指定的 3.11 执行。

### L-32 固定 runtime 闭环
- sample.pyc 用固定 3.11.15 现场生成（记录 magic/大小/SHA）；analyzer 在 marshal 前做 magic 预检：不匹配输出 `UNSUPPORTED_RUNTIME_OR_MAGIC` rc=1（无异常堆栈）；截断头 `ERROR_MALFORMED_HEADER` rc=2；损坏 payload `ERROR_CORRUPT_MARSHAL` rc=3；负控制样本 = bad-magic / incompatible-magic38 / truncated-header / corrupt-marshal 四个物理文件。

### 字节捕获与机器可读输出
- 子进程一律 `capture_output=True` 无 text（bytes）；展示 decode 用 backslashreplace；二进制输出按字节存 + SHA-256 + Base64；execution-records.json 记录每实验 A/B 的 runtime/rc/stdout&stderr SHA。
- 最终规范输出必须 0 处 Traceback/UnicodeDecodeError/TIMEOUT；S 项显式扫描（ANOMALY 正则）。

### compare_fields 的正确形态（本轮的坑）
- A/B 输出文本格式常不同（如 L-03 A="width=64" vs B="Pillow size = 64x48"）⇒ 每字段给 `pattern_a`/`pattern_b`（缺省同 pattern），kind=equal（提取值相等）或 both_success（双方各自成功，值不为否定标记）。
- 提取默认 `group=1`：group=0 返回整段匹配（含 "width=" 前缀）导致 A/B 比较恒不等。
- 输出含 repr 引号（`detected=['xor55']`）时 `\[([a-z_0-9]+)\]` 不匹配 ⇒ pattern 要容忍引号 `\[['"]?([^]]+)['"]?\]`。
- Windows CRLF：行尾 `\r` 使 `^([0-9a-f]+)$` 失配 ⇒ pattern 尾加 `\s*`。

### JSON 规格转义双倍陷阱（调试最久的一坑）
- 经 write_file/execute_code 多层传输的 regex pattern 字符串会**双转义**（文件层 4 反斜杠 = 内存 2 反斜杠 = 正则匹配字面 `\\`）。
- 修复：文件层文本把 4 反斜杠→2 反斜杠（JSON 中 2 斜杠解码为 1）后重新 json.load；**不要**把 `\[` 直接文本替换为 `\[`（非法 JSON 转义，破坏整个文件）。
- 纪律：生成 spec 后立即 `json.load` + 用真实样本输出 `re.search` 冒烟全部 pattern（编译 + 命中），再跑全量验证器；**先收集真实负控制输出再写断言**（把每个 neg cmd 跑一遍存 stdout 样本，从实际格式取可匹配标记），禁止按猜测格式写 key_fields。

### S11 负控制断言（probe2 两次 rc=0 逼出的修复）
- 原实现只查 rc∈exit_codes + 无 anomaly 字样 ⇒ 负控制样本被换成阳性时输出 rc=0 无异常 → 假 PASS。断言必须落到语义标记：
  - key_fields 静态匹配：`f"{k}={v}" in stdout`（键=输出真实变量名，如 seq_strict_continuous，不是语义缩写 strict）；
  - `_contains` / `_not_contains`：子串出现/不出现（接受型 neg 用成功特征，拒绝型用拒绝标记或"不得出现阳性特征"）；
  - `_neq_field`（如 L-82 wrong-pw：nthash 必须 ≠ 正样本输出 nthash）⇒ 与 runsA 正输出动态比较；**scalar 必须规范化为数组**否则逐字符迭代（neq:n/neq:t/neq:h）。
- 断言源 = expected 顶层字段 ∪ key_fields，排除 exit_codes/accepted/decision/key_fields/_* 键自身（否则把 `key_fields={}` 当字段名断言，全 FAIL）。
- 恢复被 spec 重建覆盖丢失的负控制：用重复 add() 重建 spec 时后 add 覆盖前 add ⇒ L-59 non-hid、L-83 split-token 静默消失；重建后逐实验核对 neg control_id 清单与总数（36/30）。
- S11 修复后必须**重跑双入口正式树**再重跑探针；验证器中途改动 ⇒ 杀掉在跑的探针进程重跑（旧版验证器结果作废）。

### 失败探针执行纪律
- 五类：①A/B 关键字段不一致（改 B 输出 +1）→ S10 FAIL 且 S20 保持 PASS；②负控制换阳性（把阳性样本覆盖 neg 样本 + 重建临时 manifest）→ S11 FAIL 且 S20 保持 PASS；③删 expected_negative → S07 FAIL；④L-32 runtime_id 指错 → S06/S08 FAIL；非 UTF-8 全二进制输出 → 字节捕获不崩但 S10/S11 受控 FAIL（rc≠0）；⑤干净副本双入口 24/24 rc=0。
- 每次探针在 --root 临时副本做 mutation 后**重建该副本全部 manifest**（否则 S20 因 manifest 失配 FAIL，掩盖主因）。
- 7 次完整验证器运行 ≈ 25 分钟 ⇒ 探针脚本必须后台运行（notify）+ 每探针 try/except + 逐条落盘 probe-results.json（中断不丢）；日志逐行 flush；首次失败与修正后结果都保留（history 文件），final 只汇总最终五类。
- 报告必须如实写"探针首次 rc=0/24/24"事件与修复合集，禁止只写修正后。

## 交付哈希纪律（rem-03 手拼后缀事故的教训）
- 交付消息/报告里的哈希**全部在写消息那一刻从磁盘读取完整 64 位**；禁止"前缀来自磁盘 + 后缀凭记忆/推断"拼接（rem-03 报告哈希 ca983204… 前缀对、后半段错被教师点名；staged 工具哈希记忆截断 `c098c8f3…` 同型）。记忆里的哈希只作核对提示，不作交付值。
- 报告 §哈希表：绝对路径 + size + 完整 SHA-256；**不含报告自身**（自引用不收敛）；final-hashes.json 重建顺序：正文修正 → 预终验 → 表插入 → 重建 final-hashes（含新报告哈希）→ 表一致性自检（按 path 反查 items）→ 不再改文件。
- rem-03 final-hashes 因后续轮门禁追加状态块而失配的条目：更新条目 + 加 note 说明（pre-remediation 冻结保留为漂移证据），不改冻结清单本身。

## 跨轮通用纪律（本轮再次验证）
- 门禁锁文件出现 ⇒ 立即停（即使 SOURCE 双哈希已 PASS），零写入；用户关闭后**重新现场执行完整门禁**，不沿用暂停前判断。
- 每份新指令先 read_file 全文（附件路径带 Context Warning 属正常）；禁止凭文件名猜内容。
- 验证器缺陷要用失败探针暴露后再修，不在报告里声称"已修复"。
