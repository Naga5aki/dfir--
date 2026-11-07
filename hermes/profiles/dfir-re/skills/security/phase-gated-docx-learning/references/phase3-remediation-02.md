# 阶段3 二次纠错与技术复核轮（Remediation-02）完整配方

实证：2026-09-03，S1-S24 全 PASS rc=0，三类失败探针真实 rc≠0，`Phase 3 Remediation-2 Completed`。
上一轮（rem-01）报告被标 `Superseded by Phase 3 Remediation-2`（错误历史保留）。

## 1. 门禁（与 rem-01 相同 + 两处新增核对）
- 锁文件不存在；SOURCE 双 SHA-256（两次之间完整 ZIP 部件读取）；阶段2 冻结 13 项；Memory 5 锚点。
- **manifest 现场条数核对**：rem-01 报告写"387 条目"而现场复算 389 ⇒ 以现场为准，登记 rem-01 数字失配；不得沿用任一数字直到最终重建。
- 全量清点（450 文件/36 目录/36 result/README/manifest）；建 `remediation-02/pre-remediation-files.sha256` 冻结清单。
- 状态块 `Phase 3 Remediation-2 Required` 追加到原报告/rem-01 报告/checkpoint 顶部。
- 指令路径笔误处理：教师写 `D:\CTF\_MISC\_Tools`，现场唯一存在 `D:\CTF_Misc_Tools` ⇒ 以现场为准并登记（不臆断为另一目录）。

## 2. 输出不可变规则（教师 §三，硬性）
- 既有 `outputs/run-output.txt` = 历史证据：不覆盖、不删改、不在末尾追加"v2 已通过"。
- 每次新运行写不可变文件：`outputs/remediation-02-analyzer-a/b.stdout.txt`、`.stderr.txt`、`remediation-02-controls.stdout.txt`、`remediation-02-command-record.json`。
- command record 至少含：完整命令、cwd、开始/结束时间、退出码、输入文件 SHA-256、输出文件 SHA-256、工具/解释器绝对路径与哈希。
- result.json 的 actual/assertions/functional_assertions/method_a/b/positive/negative_control/observation 等必须引用本轮新输出，不得只引用旧输出。
- 所有被修改实验的 manifest 在**全部运行与结果更新结束后**统一重建，重建后再全量复算。

## 3. 协议正确链（教师技术复核确认；此前两轮实现均有错）
### SNMPv3 USM（RFC 3414 §2.6/6.3/A.2-A.3）
- **无 64 轮迭代**！正确链：Ku=H(密码循环扩展至 1,048,576 B) → Kul=H(Ku ‖ snmpEngineID ‖ Ku)（仅一次本地化）→ 报文 12B msgAuthenticationParameters 清零 → authParam=HMAC-H(Kul, wholeMsg)[:12]。
- 64 是 RFC 样例密码缓冲块大小 / HMAC pad 长度，不是迭代次数。rem-01 误加 64 轮 ⇒ 工具对错误构造不命中 ⇒ 错误结论"工具不符合 RFC"——实际 snmpv3brute 的 hex 扩展+'0'*96+ipad/opad 恰为标准 HMAC（16B Kul 零填充至 64B），符合 RFC。
- 锚点：RFC A.3 "maplesyrup" 向量禁网不可得 ⇒ 用工具池只读 `snmpv3_multi_master.pcapng`（15960 认证报文）提取真实报文，staged snmpv3brute 全词表命中 `snmp_password`(SHA)，A（标准 hmac）/B（手工 ipad/opad+逐块 1MiB）auth12 一致 ⇒ 三方闭环。
- 实现 B 时注意：手工 HMAC-MD5 内层必须是 MD5（曾误用 MD4 致中间量不一致）；key>64B 折叠用 MD5(key)。

### NetNTLMv2（MS-NLMP 3.3.2）
1. NTHash = MD4(UTF-16LE(password))
2. ResponseKeyNT = HMAC-MD5(NTHash, UTF-16LE(UPPER(user) ‖ domain)) —— rem-01 漏了这步（直接拿 NTHash 当 key）
3. temp = 0x01010000 ‖ Z(6? 实际 8B RespType 区) ‖ Timestamp(8) ‖ ClientChallenge(8) ‖ AV 对(域=0x0002, 服务器名=0x0001) ‖ EOL(0x0000)
4. NTProofStr = HMAC-MD5(ResponseKeyNT, ServerChallenge ‖ temp)
5. 5600 行 = `User::Domain:ServerChallenge:NTProofStr:Blob(=temp)`（SC 在 NTProof 前！rem-01 写反）
- MsvAvNbComputerName = 服务器/计算机名，**不是用户名**。
- **用户名大小写变体不是负控制**（ResponseKeyNT 先 Uppercase ⇒ user42 与 USER42 结果相同——这本身是合法语义验证）。
- 合法负控制：错口令 / 不同用户名字符 / 错域 / 错 SC / 错 CC / 损坏 TargetInfo。
- B 方法须独立纯 Python MD4（RFC 1320 自实现，用 empty/a/84B 向量校准）+ 手工 HMAC；A 用 Crypto.MD4 无妨。
- hashcat 无设备 ⇒ 只能证明格式/派生链，不能声称真实破解。

### OBEX（IrDA OBEX 1.3）/ ATT（Bluetooth Core）
- OBEX PUT 判定 = `(opcode & 0x7F) == 0x02`（final/continue 位掩掉；GET 0x03 不算 PUT）。
- Name header(0x01)：长度含 header 本身、UTF-16BE、NUL 终止；Body(0x48)/End-of-Body(0x49) 多包重组，缺 EoB=不完整。
- 边界负控制：非法 packet length（声明>实际）/ header length<3 / 截断 Unicode 无 NUL / 缺 EoB / 非 PUT。
- ATT 多字节字段 **little-endian**（handle 用 `<H`，rem-01 用 `>H` 错）；0x12 Write Request 与 0x1B Handle Value Notification 分开验证；截断/错 opcode/空值负控制。
- 混合实验总状态 = 最低子范围（Fermat CV + OBEX LR + ATT LR ⇒ 整项 LR，子范围分别保留）。

### TS-over-UDP / AVIF
- 恢复完整性 = recovered bytes 与源 TS **SHA-256 全等**（曾 21996≠22748 却称无损——pcap 实际 121/121 全包在，是 analyzer 丢 PAT/PMT）；CC 连续性按 PID 分组；丢包=INCOMPLETE（解析成功不覆盖缺口）；同 PID 乱序可窗口重排恢复；无 RTP/应用层序号时跨 PID 全局乱序声明不可唯一恢复。
- av1C（ISO 14496-15 AV1CodecConfigurationRecord）：byte0=marker(1)+version(7)（marker 恒 1）；byte1=seq_profile(3)+level(5)；**byte2 bit6=high_bitdepth**（rem-01 误读 byte0 bit7 ⇒ 恒 1 无法区分 8/10-bit）。10-bit 双证据=容器 av1C.high_bitdepth=1 + ffprobe pix_fmt=yuv420p10le。

## 4. 验证器重建 V1-V9 → S1-S24（rem-02/scripts/verify_stage3_remediation_02.py）
- 只读：正式树模式不创建/修改/删除任何文件；支持 `--root <临时副本>`。
- S5(V1) CV 双方法=真实运行结果比较：analyzer-a/b 存在、互不 import/不读 truth、文件哈希不同、**rem-02 新输出存在**（glob `remediation-02-analyzer*.stdout.txt` 命名变体）、功能断言≥3。
- S6(V2) 正控制非空 + 每负控制真实执行；参数型控制也须独立命令与输出；不检查目录非空即 PASS。
- S7(V3) source∈TOOL_SOURCE、staged∈本轮暂存目录、源=复制后=运行后三 SHA-256 相等、源现场哈希复核、命令记录 staged 路径、系统工具与工具池分栏。
- S8(V4) memory-candidates 仅 CV/LR，每条含 validated_scope；Partial/Tool-Gap/Blocked/Contradicted 全排除。
- S9(V5) 动态泄漏：hex40+/hex32/base64/IP 通用正则 + 样本词表；白名单需逐条说明协议常量。
- S10(V7) 跨文件统计：现场 result 计数 == experiment-results.json == register 36 行 == checkpoint `CV+LR = N` == rem-02 报告 `CV n / LR m`；**全文无 `or True`**。
- S4(V9) evidence_integrity.remediation_end_match = `{checked:true, manifest_match:true, checked_at, verification_record}`（不得留"待终验"文字）。
- S14 manifest 全量复算 0 parse/0 missing/0 hash/0 unlisted。
- 旧验证器 superseded：写**独立 notice 文件**（superseded-notice.md），不编辑 rem-01 冻结文件。

## 5. 失败路径真实探针（教师 V8）
临时副本（shutil.copytree 到 %TEMP%）制造三类缺陷后以子进程运行验证器 `--root`：
1. result.json 状态置非法值 → rc≠0
2. manifest 某行哈希改 0*64 → rc≠0
3. CV 实验删 analyzer-b.py → rc≠0
另：无缺陷副本 → rc=0。全部 stdout/stderr/rc 存档 failure-probe-output.txt。禁止"改正式文件再恢复"。

## 6. Windows 字节/哈希纪律（本次唯一误触事件）
- python `open(path, 'w')` 文本模式在 Windows 会把 `\n` 写成 `\r\n`（+1B/行）⇒ 用 universal newline 读回再写回会**静默改变文件哈希**。
- 恢复哈希冻结文件必须 `rb` 读 + `wb` 写（或 newline=''）。
- 冻结/历史文件（rem-01 产物、final-hashes 清单内文件）视为只读：需要标注 superseded 就新建 notice 文件；确需修改时先披露并更新对应 final-hashes 条目+note。
- rem-01 验证器被误触事件教训：加注释→回滚后内容语义复原（自验 20/20）但字节哈希仍差（前 22 hex 同）——无原字节参照时不要反复试写（每次尝试都是新的历史修改）；改为披露+更新清单条目。

## 7. 状态重算（现场为准，不硬编码教师预计值）
rem-02 终态：CV 21 / LR 8 / Partial 1（L-06，dispose/blend 未验证保持）/ Tool-Gap 6。
CV 21: L-01/02/03/07/14/18/33/38/46/49/56/58/63/66/67/69/72/78/80/81/82
LR 8: L-11/21/32/41/59/64/83/84（L-83、L-84 自 CV 如实降 LR）
CV+LR=29≥24、CV=21≥18。memory-candidates 29 条，动态泄漏扫描 0。

## 8. 交付物（rem-02 目录）
pre-remediation-files.sha256 / issue-register.md / targeted-results.json（10 项定向）/
verification-output.txt / failure-probe-output.txt / tool-source-and-stage-manifest.sha256 /
scripts/verify_stage3_remediation_02.py / superseded-notice.md / final-hashes.json（不含自身）。
36 实验目录 outputs/ 下新增 remediation-02-analyzer*.stdout.txt（+L-81 command-record.json）。
报告：reports/misc-knowledge-summary-phase03-remediation-02.md。
资源计数：下载/联网/安装/升级/服务/发包/认证/无线发射/未知载荷执行/Memory 写入全 0。
