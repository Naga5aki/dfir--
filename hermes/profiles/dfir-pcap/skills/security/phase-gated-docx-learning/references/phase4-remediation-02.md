# Phase 4 Rem-02 盲测重建轮配方（教师复验 72/100，2026-09-05 实证）

教师复验后判定：迁移首轮 25/29 与纠错 29/29 **全部作废**——solver 硬编码一次性 marker
（TRANSFER4/TR4/消息值）构成先验污染；方法 B 非独立；observation 6 时间戳=自报。重建为
**盲测架构**（analyzer 冻结先于样本生成），当前进度：首轮 **21/29**（A 集合独立通过），
FAIL 8 项待纠错（TR-10/17/18 真解 + B 集合五项实现缺陷）。

## 架构顺序（严格）
1. **analyzer A/B 先冻结**（对任务机制写求解函数，零样本内容先验）→ 2. comparison spec 预冻结
→ 3. 样本生成（新随机参数）→ 4. 密封 truth → 5. wrapper 盲测作答（正样本+neg）→ 6. 评分。
analyzer 在样本生成后不得按样本定制（纠错只修通用 bug 并记录）。

## Analyzer 约束（教师 M1 的正面化）
- **零 marker/truth 常量**：禁止 TRANSFER4/TRAINING_P3/TR4*/消息值/口令/样本常量——用
  `grep -cE "TRANSFER4|TRAINING_P3|TR4MP3|_L[0-9]+_" analyzers_*.py` 断言 0 命中。
- 判定只用**格式不变量**（PNG 签名/ELF magic/TS 0x47/zlib 789c/ID3/MP3 bitrate 表/NMEA XOR
  校验和=公开标准）与**通用可打印性启发**（最长全可打印段/可打印比率选族）。
- **机制参数外置 params.json**（生成器产出的任务公开参数：patch 值/offset/note_base/user 名/
  n 值/词典文件名）。样本常量（如 SNMP user 名）必须 params 化，analyzer 不得硬编码
  （`par.get("user","transfer_user")`）——替换时**保持 if 块缩进**（曾把 if 内 3 行顶格致
  模块 import 崩、整集合全 FAIL）。
- 消息文本=解码客观结果可以输出（消息是题目内容不是先验），禁止的是"搜 marker 定位/判定"。

## A/B 独立实现对照（双集合 58 函数）
查表 vs fromhex；marker 链推进 vs 全字节扫描/尾部反向定位；过零率窗 vs Goertzel 能量；
简化字节扫描 vs vlq 变长+运行状态解析；box 递归树 vs 字节 find+cfg 直读；math.isqrt vs
增量平方判别；固定偏移 vs IHL/188 网格；digest 比较 vs 显式折叠密钥重算。

## 执行包装器（observation 自动记录，业务 analyzer 零自报）
wrapper 子进程真实运行 analyzer，自动记录 run_id/命令/入口文件 SHA/输入目录 SHA/start-end/
rc/stdout+stderr 哈希/结果文件哈希。陷阱：
- **`text=True` 必须显式 `encoding="utf-8", errors="replace"`**——Windows locale(GBK) 解码含
  非 ASCII 的 analyzer 输出（乱码流/拉丁字符）抛异常 → 结果 core=null 但 rc=0（静默丢结果）。
- stdout 解析取**最后非空行**（print 尾换行使 splitlines()[-1] 为空）。
- rc!=0 也落 stderr_head/stdout_head 诊断字段。
- 全量 116 次（A/B×29 正+neg）约 10-15 分钟（TR-29 Fermat 一次 ~88s）；驱动里单次
  subprocess timeout 600；曾整体卡在 TR-27 neg 600s（损坏 dico 触发长路径）——分段补跑即可。

## Pack 生成（第三次复现 truth.json 泄漏！）
- **泄漏根因=collector `os.walk(genwork)` 把含 truth.json 的全文件复制进 solver-pack**
  （generator 单产物=truth 的项尤其）——修收集逻辑（walk 排除 truth.json），别只清理。
- 密封核对脚本逐 TR 断言：无 truth.json/有 neg/有 task.md/输入齐。
- **neg=同名损坏文件**（analyzer 读取名固定，改扩展名=找不到文件）：头毁 8B+中部翻转+尾截断；
  损坏使文本类 analyzer UTF-8 解码崩 → rc=1 即"失败特征"，评分器对 rc!=0 的 neg 记通过。
- 单产物 TR（generator 只写 truth.json：TR-14/27/29）输入从 **genwork 内 generator 源码常量
  重建**（不重跑 generator——r4 随机重跑=内容变，与已密封 truth 不符）；msg 常量正则要匹配
  `hmac.new(k, b"message")` 形态（无 `msg =` 行）。
- OBEX 头构造=**tag(1B)+len(2B BE，len 含自身 3B)**（先 tag 后 len；曾倒序致 Body 文本错位）。
- genA EXTRA v3 替换用行级正则（引号/转义层数三坑：tool JSON 输出 `\\x` 显示=字面 `\x`，
  以 grep 原样为准；替换后语法检查+打印目标行确认）。

## 评分器（spec 驱动，规范化预冻结）
- spec 键 vs truth 实际键 vs analyzer core 键 **三层键名逐项映射**（truth_ovr→ovr_sha、
  entry_hex/entry32_hex 任一、w→width、msg1→note_bytes、pts→coords、data_bits 等）；
  compare_one 每 TR 特判集中一处，别散落补丁。
- 规约：hex_0x 对 int 用 `format(v,"x")`（str(int) 得十进制串）；周期 XOR 密钥最短周期减半规约；
  文本比较 strip 帧标志（AFSK `~msg~`）；TR-02 判定=sha256(bytes.fromhex(truth_ovr)) 重算
  （truth 存 hex 串不是 sha）。
- truth 契约核对：generator 无 truth.json 时 genA fallback 写 input_hashes → 必须按任务语义
  重建（TR-28 winrm_like per-file 由 pcap HTTP 序列嗅探判定）；TR-29 补 obex_content。
- TR-04 双独立 zlib 流=**段数据 0x789c 起始开新流**分组（单流拼接连解会 zlib.error）；
  评分 type4 段列表 sha 含 truth。
- 首轮 PASS=(A_ok or B_ok) and ab_ok——A 过 B 不过（B 实现缺陷）也会整项 FAIL；B 独立路径
  假设必须先对照样本真实结构（b_tr22 头部复制假设在 v3 不成立=b 全空）。

## 本批事故簇
- execute_code 写含 `'''` 的代码字符串 → 外层三引号提前闭合，后续内容被当真代码执行
  （ModuleNotFoundError Crypto）→ 内嵌 code 用单行拼接/转义，写完 py_compile。
- 行替换把 `def b_tr02(indir):` 与下一行粘成一行/缩进错乱（多轮 replace 叠加）→ 出问题时
  直接按函数边界整体重写干净版，别继续打补丁。
- py_compile OK ≠ 逻辑对（user 参数化缩进毁坏只在子进程 import 时爆）→ 修改后先单 TR 冒烟。
- 静态核对 analyzer 硬编码读文件 vs TR 目录：`re.findall(r'join\(indir,\s*"([\w.-]+)"\)')`
  提取比对（params/dico.txt/hex.txt 为公共名放行）。
- 评分映射优先于怀疑 solver：多数"FAIL"是评分器键名/规约缺，先修评分器再判真解错。

## 剩余纠错轮待解（2026-09-05 状态）
- A 侧：TR-10 base 恢复（勿假设 range(32)，从 t-变体直接逆推）；TR-17 HID usage 差 1
  （truth typing 与 A 差 1 键）；TR-18 输出空（包遍历未产——查 while 偏移与族循环）。
- B 侧五项：b_tr05 尾部反向定位空、b_tr12 只出 sha 无文本（补极性/位序组合流）、
  b_tr21 尾帧 231（帧长自洽过严——末帧无后继时放宽）、b_tr22 头部复制假设（改尾 512 读）、
  b_tr25 188 网格重组出垃圾（sync 对齐/段处理）。
- 通过线：首轮 ≥25/29（证据/安全错 0）；终态仍受闭卷无题包限制。
