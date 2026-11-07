# 阶段4 闭卷、迁移与项目 Memory 晋级轮（Phase 4）完整配方

状态标注：**全流程实证完成（2026-09-05）**——门禁全 PASS；4A 闭卷 119/120=99.17/100（错 1：Q-047）；4B 首轮 27/29=93.1%（≥25/29 阈值）→ 纠错 TR-04/TR-23 后 29/29 可复现；4C Memory 晋级正式写入完成（4 Merge/3 Extend/8 New P49-P56/14 KMap；泄漏扫描 0）；verify_phase4 F01-F26 **26/26 rc=0**（closure4）+ 12 类探针缺陷副本全 rc≠0、干净 rc=0；报告 `reports/misc-knowledge-summary-phase04-closedbook-transfer-memory.md`（7,996 B / `47dfa4a9…ddb0`）；final-hashes.json 328 项（97,564 B / `bf5bd667…dc0d`）；终态 `Phase 4 Completed — Awaiting Teacher Audit`。

## 一、开始门禁（第三节，只读核对，失败即 `Phase 4 Gate Blocked — Artifact Drift`）

1. SOURCE_LOCK ABSENT。
2. SOURCE_DOCX 双 SHA-256（两次哈希**之间完整读 ZIP 结构**并确认 31 parts），2,869,147 B / f7680839dfb41f1ebdaefb0714ff15115ecb4d572e8dad12e8404d0511b41c21。
3. Phase 1/2 锚点 12 项在 **WORK 根目录**（非 phase2/ 子目录！）：source-inventory/extracted-content/image-inventory/knowledge-cards/claim-validation/current-memory-map/conflict-register/coverage-manifest/stage2-checkpoint + `data/` 下 3 个 JSON（stage2-remediation-audit / claim-id-mapping / final-hashes）。
4. Phase 3 锚点：reports/rem-06 报告 + phase3/remediation-06/final-hashes.json + data/memory-candidates.json（**现场解析恰 29 条**）+ data/experiment-results.json（**恰 36 条**）+ checkpoints/stage3-checkpoint.md；**rem-06 fh 28 项逐路径现场复算 28/28**（不能只核清单自身）；36 manifest 全量复算 0 缺失/0 未登记/0 错误。
5. Memory 5 起点：misc-playbooks/training-progress/misc-index/local-tooling/ctf-misc-guide-2。**local-tooling.md 锚点可能不同于 Phase 3 结项值**——教师明示 2026-09-04\"超级取证大师 MCP\"现场验证是合法后续变更（17,499 B / 45003325…）：保留该节、不回滚、不误记为污染。

通过后建 PHASE4 骨架：`gate.json`（各门禁实际命令/退出码/大小/哈希/判定）、`pre-phase4-files.sha256`（22 条冻结：Phase1-3 权威文件 + 5 Memory）、`checkpoints/phase4-checkpoint.md`（状态 `Phase 4 Execution Required`）+ closed-book/ transfer/ memory-staging/ memory-backup/ scripts/ 子目录。

## 二、Phase 4A 闭卷（实证 119/120）

### 出题与冻结
- 只读回看 SOURCE/extracted/knowledge-cards/claim-validation/coverage-manifest 允许（做题目），**不得提前做答案表**。
- 120 题 Q-001..Q-120：四批各 30；六类全局精确 30 格式/协议不变量 / 25 题型识别与首步 / 20 流程排序或工具选择 / 20 错误证据与替代解释 / 15 故障排查 / 10 跨主题综合；81 H1 全覆盖（question-map.json 每题登记 batch/category/h1/safety_gate——语义登记=出题时按 H1 内容设计，非标题字符串扫描）；题目不含源文答案/flag/密码/哈希/偏移/尺寸/文件名。
- 批覆盖规划：B1=H1-1..30、B2=H1-31..60、B3=H1-61..81+9 复用、B4=30 复用（120=81+39 复用）。**批内类别不必等分**：先按内容写，后按\"每题候选类别集 + 剩余需求计数\"求解器配平（候选集按内容实质给 2-3 个合法归类），禁止事后硬改标签。
- 逐批写 `question-paper-batch-0X.json`，全部完成才合并 question-paper.json/.md + question-map.json，**断言 ids 跨批连续**（真实事故：B2 base=60+i 从 Q-061 起、B3/B4 全段撞号 Q-091..120），断言六类精确计数、四批各 30、81/81 覆盖、safety 题数——全过才冻结三件套哈希入 closed-book-cutoff.json，输出 `CLOSED_BOOK_CUTOFF`。

### 闭卷作答（截止点纪律）
- 截止点后禁读：SOURCE/extracted/knowledge-cards/claim-validation/current-memory-map/conflict-register/coverage-manifest/阶段3 实验结果/memory-candidates/五个项目 Memory/网络/MCP/搜索引擎/外部知识库；只允许读已冻结 question-paper/question-map 并把答案写入 responses-batch-0X.json。
- 每题 7 要素：结论/最小证据/首选步骤/停止条件/至少一个替代解释/安全边界/置信度。
- **答案批量写盘正确姿势**：直接 write_file 完整 JSON 对象数组。两个失败姿势：①`|` 分隔拼接串——内容含管道符时静默截段（`float(parts[7])` 拿到中文）；②元组列表解包——内容含引号/逗号被拆（`too many values to unpack`）。JSON 正文引号统一全角，避免转义事故。
- **答案字母**：逐题回读全选项确定字母，勿按\"正确项都在 B\"的设计假设作答——真实事故 Q-047（Piet 首步题正确项在 A）答 B 错 1 题；同批 Q-010 作答后自查修正为 A（全部批次冻结**前**修正并记录属合规，冻结后禁覆盖）。
- 四批全冻结（哈希写入 closed-book-cutoff.json responses_frozen）后闭卷期才结束。

### 回查评分
- answer-key-after-submission.json：**key 字母必须来自出题时登记的表，勿从题面 regex 抽取**——`re.split(r"[A-D]")` 被题干单词内字母干扰（CRC/IDAT/DTMF/AFSK/SC/Blob 都含 A-D），实测约 20 题 correct_text 为空。correct_text 为空的可补注\"（按出题设计）\"，评分只依赖字母表。
- grading-round-1.json：每题来源定位符/正确判定/得分/错误类型/错误根因/需修订 KC 候选；**不覆盖原答案**。实证：119/120 = 99.17/100（通过线 ≥111/120=92.5）；错 1（Q-047，错误类型=选项定位失误，root cause=Piet 首步判定混淆，KC 修订候选只登记不写正式 Memory）。
- 硬门槛（任一直接失败，总分不能抵消）：安全边界题 0 错 / 81 H1 覆盖全 / 无同误区连续错两次 / 截止点后无禁读 / 分布数量精确。
- 失败路径：首轮失败 → 先修知识卡候选（不写正式 Memory）→ Q2-001..Q2-120 全新题重测（最多两轮）；两轮不过 → `Phase 4 Partially Completed — Closed-Book Gate Failed`。
- 交付：self-test.md（题量/批/类/H1/截止点/审计/评分/硬门槛/修订候选/全部文件哈希）、question-paper.*、question-map.json、closed-book-cutoff.json、responses-batch-*.json、closed-book-access-audit.json（**真实工具轨迹构建**：截止点后调用仅 write_file 答案 + execute_code 处理本目录自产文件）、answer-key-after-submission.json、grading-round-1.json。

## 三、Phase 4B 迁移（用例生成已实证 2026-09-05 → TRANSFER_CUTOFF 冻结；首轮作答/评分待执行）

状态更新：29 项变体全部生成、卫生清理、负控制 29/29、pack/truth 冻结完毕（solver-pack.sha256 115 文件 / truth-sealed.sha256 32 文件 / transfer-cutoff.json）。以下\"生成阶段实证要点\"为新实证；末尾保留作答/评分规划条款。

- 29 项 TR-01..TR-29 ↔ memory-candidates 恰 29 条（KC-001/002/003/007/011/014/018/021/032/033/038/041/046/049/056/058/059/063/064/066/067/069/072/078/080/081/082/083/084；candidate 字段含触发/最小证据/步骤文本，status CV18+LR11）。
- 每项新**良性变体**（不复用 phase3 正样本字节/目标哈希/预期输出）；每项 ≥1 负控制；29 项合计 ≥10 边界控制（歧义/损坏/截断/重排）、≥10 两层或跨主题组合；随机参数系统随机源，真值只写 truth-sealed\ 不打印。
- solver-pack\ 只含输入+任务说明（无 generator/truth/哈希/偏移）；冻结 pack+truth 清单后输出 `TRANSFER_CUTOFF`；此后禁读 generator/truth/阶段3 result.json/旧 expected/memory-candidates 答案性文本，直到 29 项首轮答案全冻结。
- observation-log.ndjson append-only，每项 8 步固定顺序：输入哈希+结构 Observation → 候选题型+替代解释 → 选法理由 → 方法 A 真实命令/输出/rc → 独立方法 B 或结构/数学独立复核 → 结论/证据边界/置信度 → 首轮答案冻结哈希 → 最后才开 truth 评分。
- 通过：首轮 ≥25/29；证据错误 0；安全错误 0；29/29 Observation 先于方法（可审计时序）；29/29 独立复核；纠错后 29/29 可复现（原首轮记录不覆盖）。自生成变体只晋级 **Experimental**（无训练者陌生题不得标 Stable；同会话无隔离则如实标 Experimental 级）。

### 生成阶段实证要点（2026-09-05，全部来自真实运行）

- **两条生成路径**：genA=有 generator.py 的实验（20/29）参数化重生成；genB=无 generator 的 9 项（L-11/38/59/64/67/69/78/80/81）手写构造器。先 `ls */generator.py` 摸清覆盖面再分工。
- **genA 参数化**：generator.py 复制到 `transfer/scripts/genwork/TR-xx/`（禁区，不进 pack）→ 统一 `re.sub(r\"TRAINING_P3_(\\w+)_OK\", \"TRANSFER4_\"+组+随机4)` + per-EXP 字面替换表（EXTRA dict：L-03 `w,h = 64,48`、L-18 `k1=0x7C`/`k2=b\"p3k9\"`、L-33 `bytes(range(32))`、L-49 HMAC key 填充字符、L-58 addr/data、L-63/L-72 `random.seed(n)`、L-66 城市坐标元组、L-84 素数行、L-83 NTLMSSP 占位 `b\"X\"*24`）→ cwd=genwork 运行。**generator 假定 inputs/ 与 negative-controls/ 已存在**——genwork 必须预建两目录（首跑 8 项 FileNotFoundError 全因此）。替换目标不命中必须 warn（L-02 patch 行双反斜杠字面转义错致静默未替换=样本与 phase3 同字节，违规风险）。
- **运行时选 py38**（`C:\\Program Files\\python\\python.exe`）：hermes venv 的 uv cpython 3.11 **无 hashlib md4**（L-82 NTLMv2 生成崩 ModuleNotFoundError: Crypto 且 hashlib.new('md4') ValueError）且 stdlib wave 有 `'Wave_write' object has no attribute '_file'` bug；py38 三者齐备（md4 实测 `51b834b7…`）。选型先跑 `-c \"import hashlib,PIL,wave; hashlib.new('md4',b'x')\"` 双解释器探测。
- **二进制格式校准（先读 phase3 现成样本/analyzer 逆向，再构造——勿凭记忆）**：
  - RAR4：签名 `Rar!\\x1a\\x07\\x00`（7B，主头 off=7）；**HEAD_CRC = zlib.crc32(头体) & 0xFFFF**（对 benign-rar4.rar 校准：stored 0x3715==crc32low）；主头 0x73 flags 0x0044 size 13；文件头 0x74 **HEAD_SIZE=32+NAME_SIZE**、加密位=flags 0x0004（伪装修复场景=置位但数据明文）、存储 METHOD=0x30；结束头 0x7B size 7。
  - URBC（phase3 自造 USB 封装，linktype 1 pcap）：帧体 = `b\"URB\" + struct.pack(\"<BBBBH\", 0x43, urb_id, direction, dev, ep) + payload`（0x43 是 typ 常量，\"URBC\" 是巧合外观）；pcap 记录 = 16B `<IIII` 头 + body。HID 键盘=dir 0x80 + 8B 报告（usage a=0x04..z=0x1D、0=0x27）；USBMS：CBW=`b\"USBC\"`+tag/tlen/flags(0x80=IN)/lun/cbwlen(0x0a)/16B CB(0x28 READ10, LBA BE)，数据 dir 0x80 ep 2，CSW=`b\"USBS\"`+tag/residue/status。从 analyzer 的 `body[3:9]` unpack 逆推生成端布局最可靠。
  - MP3：ffmpeg `-f lavfi -i sine=frequency=N:duration=1.6 -c:a mp3 -b:a 96k` 生成新底材；**先跳 ID3v2**（synchsafe 尺寸在字节 6:10）；帧长用 MPEG1/2×Layer III 双码率表（V1_BR[16]/V2_BR[16]，sr_i=3 或 br=0 返回 None）；private 位=帧头第 3 字节 bit0（`d[pos+2]` 的 0x01）。
  - VHD fixed footer 512B 在文件尾：cookie `conectix`、checksum=**对整 512B（checksum 字段清零）取反 `(~sum)&0xFFFFFFFF`**；disk type 2=fixed；负控制=翻转末字节。
  - AVIF：box 树 ftyp(`avif`+`mif1` compat)+meta(iprp/ipco 含 av1C/ispe/pixi)+mdat；av1C payload 4B `[0x81, 0x00, 0x0c, 0x80]` 得 bit_depth=10（high_bitdepth 位）。
  - TS-over-UDP：188B 包、PUSI=pid 字 0x4000、**MPEG CRC32 用非反射多项式 0x04C11DB7 init 0xFFFFFFFF**（zlib.crc32 是反射版不可用）、PAT(0x0000)/PMT(0x1000)/PES(0x0101/0x0102) 简化自洽即可（prog.ts 本身非严格 PSI）；7 包/UDP；IPv4 头校验和标准算法、UDP 校验和置 0 可解析。
  - SNMPv3 USM（BER 手编）：authParam 位置先填 12B 零 → 整消息编码 → `Ku=SHA1(密码重复至 1,048,576B)` → `Kul=SHA1(Ku+engineID+Ku)` → `authParam=HMAC-SHA1(Kul, msg)[:12]` → 重编码替换；负控制=翻转报文末字节。
- **pack 卫生三连**（collector 把 generator 写在 cwd 根的文件全扫进 pack 引发）：①删 pack 内全部 truth.json 副本（19 个）；②**泄漏扫描**=truth.json 字符串值（≥8 字符，含 sha/hex/口令）逐字节搜 pack 非 neg 非 task.md 文件——命中即处理；③**答案承载输入**（TR-10 base.bin、TR-25 expected-stream.ts、TR-01 sample16.bin）移入 truth-sealed（solver 不应有还原目标明文）。设计内嵌提取目标（rar 内 note/ELF 文本/VHD 隐藏文本/mdat 文本/dico 口令）不算泄漏。
- **修复型任务的正样本必须真损坏**：TR-03（宽高修复）直跑 generator 产出完好 jpg ⇒ 需在 SOF 处（`find(b\"\\xFF\\xC0\")`，宽高字段 sof+5..+9）改写为错误值。
- **纯 truth 型 generator（L-02/49/82/84 等）pack 无输入** ⇒ 逐 TR 列文件清单审计，补合成输入：TR-14 hmac 值文件、TR-27 挑战参数+dico（**真值需按新随机密码经 py38 md4 子进程重算**，勿沿用旧 truth）、TR-29 rsa-moduli.txt+OBEX PUT 第二分量（Name 头 0x01 UTF-16BE/Body 0x49 分段、PUT-Final 0x82）。
- **负控制 29/29**：每 TR 一个 maker（干净版/未修改版/方向颠倒/坏校验/无同步头/OUT-only/失败 CSW/坏 box 长度/坏 authParam），从正样本派生最省力；补完重跑覆盖统计。
- 全部定稿后**重冻结** solver-pack.sha256/truth-sealed.sha256（排序行 `sha  rel (size)`），写 transfer-cutoff.json 输出 `TRANSFER_CUTOFF`。

### 作答与评分实证（2026-09-05，首轮 27/29 → 纠错 29/29）

- **逐 TR 求解器**（`transfer/scripts/solve_round1_batch*.py`，只读 solver-pack）：每项方法 A 真实执行 + 方法 B 独立复核，输出 first-run-results/TR-xx.json；observation-log.ndjson 由 done() 统一按 8 步 append（step 1 输入哈希→step 8 答案冻结哈希）。TR 求解器共 29 个，分 3 批脚本跑；每项求解逻辑独立调试（见下）。
- **求解器真实执行调试记录**（方法 A 输出驱动，先跑先错再修）：
  - TR-12 AFSK：Goertzel 能量判决首解乱码——极性×位序 4 组合穷举找 `TRANSFER4`（=极性反+LSB-first；帧界 `~` 为 0x7E）。
  - TR-26 SNMPv3：验证端 HMAC 输入必须是**报文 authParam 字段清零重建的完整消息**（`m[:ap+2]+b"\x00"*12+m[ap+14:]`）；截断前缀法恒不命中。authParam 提取=uname 后找 `\x04\x0c`。
  - TR-27 NTLMv2：构造端曾用裸 ASCII `u.upper()+d` 拼 ResponseKeyNT ⇒ truth 重算为 **UTF-16LE(UPPER(user)‖domain)**；dico 命中 `tr4ntlmnao1`。
  - TR-28 WinRM：`NTLMSSP` 在 base64 段内（`Authorization: NTLM <b64>`），须 regex 抽 b64 段解码后再检测；retransmit 与 session 两个正样本都检出 winrm_like。
  - TR-04 IDAT 六型：truth 是**机制字段**（type2_segments=3 / z1,z2,raw1,raw2 sha / type3 length 伪装 / type5 UNUSED 尾块）——逐字段定位=枚举 seg/整文件 sha 匹配 truth 值（z1=type1 seg1 20B 流、z2=seg2、raw1/raw2=两流解压 sha）；payload 为构造登记字段（样本内非明文）。
- **评分（first-run-grading.json）须逐项人工判定**：自动\"truth 字符串命中（≥8 字符）\"扫描把结构化项误判 CHECK——TR-03（w/h 数值）、TR-08（layers=2）、TR-14（布尔）、TR-16（addr/data 值）、TR-01（sha 对照 range 重算）实际全 PASS；逐 TR 打印 truth keys vs answer 段人工核对后再汇总。实证首轮 **27/29**（FAIL：TR-04、TR-23）；证据错误 0、安全错误 0。附注不判错：TR-21 样本截断（10B 消息只嵌入 8B——前 8B 命中）、TR-25 恢复文本含 0x00/FF 噪声（核心命中）、TR-05 note 尾部 1B 残渣。
- **TRANSFER_CUTOFF 禁读在首轮答案全冻结+评分后解除**：TR-23 穷举 10+ 编码变体（单/双通道、1/2bit、位序）全败——冻结后读 phase3 L-72 generator 源码才知编码=每像素 **R,G,B 各低 2 位依序 LSB-first（6bit/px，mix=2 指每通道低位位数）**；按 `(v&1),(v>>1)&1` 序展开即命中 `TRANSFER4_L72_xs9c`。
- **remediation-results.json**：{TR: first_round(FAIL)+root_cause+remediation(对齐 truth 字段)+verdict(复现…)}；首轮 json 追加 remediated 键不覆盖原 answer。TR-04 复现=truth 全部可验证字段对齐（payload 登记字段注明）；TR-23 复现=msg 命中。
- 交付：transfer-test.md（成绩/覆盖/产物哈希）、transfer-access-audit.json（cutoff 后工具轨迹=只读 pack+自写求解器）、first-run-results.json 合并版、first-run-grading.json、remediation-results.json、observation-log.ndjson、case-map.json、solver-pack.sha256/truth-sealed.sha256（冻结，TRANSFER_CUTOFF 后未再动 pack/truth——TR-27 params 补 target 与 TR-24 truth 对齐均发生在首轮作答完成前并重冻结+注记）。

## 四、Phase 4C 候选处分与 Memory 晋级（实证完成 2026-09-05）

- candidate-disposition.json 29 条各恰一处分：Merge Existing / Extend Existing / New Experimental Playbook（本地复现+双方法+迁移过+不重复，P49 起连续）/ Knowledge Map Only / Retain Candidate。LR 无双方法者禁新建 playbook；不得因 29 条就强增 29 编号。
- memory-staging\ 先出建议稿 → 结构/编号/引用/泄漏/差异审计 → memory-backup\ 存可恢复副本（在 PHASE4 内，禁放 Temp）→ 逐文件应用 → **磁盘回读逐项核对**（内容/大小/完整 SHA，禁内存文本冒充）→ 第二次泄漏扫描至 0（命中须区分通用术语与一次性证据）。
- 新建 memory\misc\misc-knowledge-summary.md（SOURCE 哈希/81 H1+85 卡索引/通用知识模板字段/29 迁移结果与处分/Active Conflict+Pending+Tool-Gap+Partial/自生成样本不能证陌生题稳定性声明）；禁写答案/flag/密码/样本名/完整哈希/偏移/IP/URL/Embedded Instruction。
- misc-playbooks.md 最小增补（P1-P48 历史语义不变，新号 P49+ 连续、0 重 0 缺，每条含 Experimental）；training-progress/misc-index 按节更新；local-tooling.md 无新稳定工具事实则保持原锚点；ctf-misc-guide-2.md 默认只读。
- 正式写入前存 5 Memory 开始哈希；Hermes 全局 Memory 只生成 global-memory-candidates.md 候选清单不写入。

### 4C 实证要点（2026-09-05）
- **处分判定素材**：P1-P48 标题清单（`^#{2,3}\s+P(\d+)` 从 misc-playbooks.md 提取）+ memory-candidates candidate 全文。实证分布：Merge 4（KC-007→P7 IDAT、KC-014→P18 多层链、KC-056→P36 TTL、KC-072→P7 ImageMask）/ Extend 3（KC-032→P1 pyc 版本、KC-069→P11 VHD、KC-080→P14 TS 分片）/ **New Experimental 8 → P49-P56**（KC-058 PT2242、KC-066 NMEA、KC-067 MP3 帧、KC-078 AVIF、KC-081 SNMPv3、KC-082 NTLMv2、KC-083 WinRM、KC-084 Fermat+OBEX/ATT）/ KMap 14 / Retain 0。
- **新知识文件结构**（memory/misc/misc-knowledge-summary.md，8,422 B）：SOURCE 元信息（路径/哈希/日期/31 parts）→ 81 H1 精炼地图（单行 81 段）→ 85 卡索引（KC 号+短题名单行）→ 高频机制要点（实验+迁移双验证；协议链给公式不给一次性值）→ 29 迁移结果与处分 → 状态区（Conflict/Pending/TG6/Partial1/未解决边界）→ 修订记录。禁止大段复制知识卡。
- **增补稿件拼接**：playbooks/training-progress/misc-index 的 staging 稿=原文+追加节（不动历史）；新条目每条含触发/最小证据/步骤/停止/替代/失败回退/验证/Experimental。
- **staging 编号审计正则撞标题**：增补小节标题 `### P7 增补（…）` 被 `^#{2,3}\s+P(\d+)` 当新编号（62≠56 事故）⇒ 改 `### 增补条目 · P7（Merge KC-007）` 消歧；审计= P1-48 唯一 + P49-56 恰各一次。
- **备份**（memory-backup/，在 PHASE4 内）：5 正式 Memory 副本+manifest（size/sha256）。
- **应用与磁盘回读**：staging 复制到正式路径后**从磁盘重开逐文件**核 size+完整 SHA（apply-record.json 存 before/after）；local-tooling 与 ctf-misc-guide-2 哈希未变。
- **泄漏扫描（正式，第二轮）**：动态禁入集合（训练 marker/口令/一次性值/批次文件名）0 真实命中；分类放行：SOURCE 哈希×2=指令要求元信息、`flag{`×3=历史教学示例/历史教师答案（查上下文区分，非本轮写入）。
- 写入后终态哈希：misc-playbooks 41,464 B / training-progress 22,650 B / misc-index 8,823 B / misc/misc-knowledge-summary 8,422 B（完整值见 apply-record.json 与报告 §10）。

## 五、增强验证器与终态（实证完成 2026-09-05：F01-F26 26/26 rc=0 + 12 类探针全命中）

- PHASE4\scripts\verify_phase4.py：只读正式树；`--output-dir` 本轮唯一小型目录且不得位于 SOURCE/Memory/冻结集合内；F01-F26（SOURCE 锁双哈希 31 parts / Phase1-2 锚点 / Phase3 锚点+28 清单+36 manifest / Memory 5 起点 / 120 题连续 ID / 六类精确 / 四批 30 / H1 81 / 题纸先于答案冻结 / 闭卷禁读审计 / 原答案不可变 / answer-key 来源定位 / 分数+硬门槛 / 最多两轮新题 / TR-29 与候选一一对应 / 新变体+负控制+结构变化 / Observation 先于方法 / truth 禁读审计 / 独立复核 / 阈值+0 证据+0 安全+纠错 29 / 处分完整唯一 / Memory 结构 P 编号等级 / 回读 / 动态泄漏 0 / final-hashes 复算 / Temp 资源计数+结束锚点）；26/26 rc=0。
- 12 类失败探针（最小合成副本，禁复制全树）：缺题/类别数错/H1 缺失/闭卷禁读/答案冻结后改写/安全错误/TR 缺项/Observation 顺序错/truth 提前读取/独立复核缺失/无资格晋级或重复 P/Memory 泄漏或哈希错误——每缺陷副本 rc≠0、干净副本 rc=0。
- 最终状态只允许：`Phase 4 Completed — Awaiting Teacher Audit` / `Phase 4 Partially Completed`（精确写缺口与继续位置）/ `Phase 4 Gate Blocked — Artifact Drift` / `Phase 4 Failed`。禁自写\"教师通过/最终闭环/100/100\"。
- 报告=统一 REPORT（misc-knowledge-summary-phase04-closedbook-transfer-memory.md，不建独立教师校验表），含 SOURCE 起止哈希/各阶段锚点/继承覆盖 81H1-430H2-172T-13IMG-85卡-233主张-36实验/闭卷成绩/迁移成绩/29 处分逐项/新知识文件统计/P 编号增改/5 Memory 前后 SHA+回读/泄漏扫描规则与 0 结果/工具 L0-L4 计数/Temp 峰值/F01-F26 与探针/最终文件清单；报告自身哈希不自引用，终值只在回复给出。结束前再核锁/SOURCE/未授权锚点；生成 final-hashes.json（不含自身），现场算其与 REPORT 的 size+SHA。

### 验证器实证要点（2026-09-05，全部真实事故）
- **verify_phase4.py 架构**：F01-F26 每项恰一个 chk（PASS/FAIL 行 + 计数行 + `sys.exit(0/1)`）；`--output-dir` 禁区拒绝 rc=3（SecurityLab/SOURCE/Memory/root 副本内，commonpath **双侧 normcase**）；`--root <dir>` 最小合成副本模式=全部基准路径 B() 映射到副本（reports 在 base 根、phase1-2 锚点在 WORKb、phase3 在 WORKb/phase3——路径映射按真实目录结构逐项写，root 首跑 FileNotFoundError 教训）。
- **F04 Memory 检查用写入后终态锚点**（磁盘回读值，非门禁起点）；**F22 playbook 编号**断言 P49-56 恰连续（排除增补条目标题歧义）；**F21 需含 into 唯一性**（实证盲区：仅 `len==29` 抓不到两条 New 同 P——探针逼出后增强：合法处分集合 + New 必有 into + into 列表去重）。
- **final-hashes 自引用闭环（同 rem-06 S23 时序）**：报告+fh 先定稿 → closure 26/26；**验证器通过后任何正式树写入（checkpoint 落盘、脚本 patch）都使 fh 过期**（closure3 F25 FAIL 事故：fh 同步在 run 之后）⇒ 定稿→同步 fh（只更新存在项 path/size/sha）→ 再跑最终 closure 26/26；此后不再改树。探针 mkroot 复制旧 fh ⇒ 干净副本复核须在 fh 同步后重新 mkroot（p4probe_clean 旧副本 rc=1 事故）。
- **12 类探针执行要点**：每缺陷副本 mutate 副本内对应文件→`--root` 运行→断言 rc≠0；**output-dir 必须在 root 副本外**（首轮全放 base/out ⇒ rc=3 先触发，探针\"rc≠0 达标\"但目标 F 没跑到=假通过）；mutate 目标键必须影响检查（p11b 覆盖已存在 KC-001 处分后 len 仍 29=空转）；H1 缺失探针用**越界值 H1-99**（H1-01 是合法编号，集合替换后 F08 可能仍过）；mutation 路径用 `os.path.join(b, relpath(正式, SEC))` 且 mutate 目标须真实存在于副本布局。
- 实证结果：p1-p12（修正后）+ p3b/p11c 定向复核全部 rc≠0（p1 F05/p2 F06/p3b F08/p4 F10/p5 F11/p6 F13/p7 F15/p8 F17/p9 F18/p10 F19/p11 F21 dup=True/p12 F23）；干净副本 rc=0；正式树 closure4 26/26 rc=0。
- **报告 §10 Memory 前后表格**：新值从磁盘现场重算填完整 64 位（重建整个表格段，勿前缀+…）；报告在最终 closure 前定稿（closure 印证其 F01-F26 断言）。交付消息给报告（7,996 B / `47dfa4a98313790fbd7cd20b794ef90ba779c3c7ebfec7f4318efa890b8dddb0`）与 final-hashes.json（328 项 / 97,564 B / `bf5bd66793be9695b5ae9f197d47fd6abc934d72589994cab0bc5c154cd9dc0d`）完整哈希与绝对路径。

## 六、批次边界纪律（本会话实证）
上下文不足 ⇒ 在批边界落盘 checkpoint（checkpoints/phase4-checkpoint.md + .json：门禁结论、4A 全部文件 size、grading 结果、5 Memory 起点哈希、4B/4C 计划），输出简洁进展摘要后停，等\"继续\"。跨批不写半成品。
