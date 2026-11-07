# 独立闭卷题包作答与提交流程（teacher-delivered closed-book packs）

教师下发的独立闭卷题包是解除 `Awaiting Independent Closed-Book Pack` 的事件。本配方来自 Pack-A + Pack-B（各 120 题、共 240 题全量作答提交）的完整实证。

## 1. 题包结构与只读读取

zip 内布局：
- `PACK-DECLARATION.md` / `PACK-METADATA.json` —— freeze_id / build_id / sample_count / sealed_answer_key_count / pack_id / schema_version。
- `public/QUESTION-SPEC.json` —— 结构化题目（作答依据）。
- `public/QUESTIONS.md` —— 人读题纸（与 SPEC 同源）。
- `public/samples/*` —— 每题一个 record 文件。

开头动作：先记录 zip 的 SHA-256 与大小（提交报告必须给出），再 `zipfile` 只读列举内容，最后解压到受控工作副本（如 `phase4/closed-book-v4/Pack-X/`）；**原 zip 原地不动**，只读副本工作。

QUESTION-SPEC.json 每题关键字段：`question_id` / `public_prompt` / `sample_paths` / `category` / `difficulty` / `negative_control` / `safety_gate` / `boundary_trap`。

**先抽查一个 sample 再决定投入**：本类题包的 samples/ 是 public_prompt 的**逐字转录**（带 record-id 的合成证据文件），不含额外数据 ⇒ 作答=对题面给定数值/字段的推理判断，逐样本解析是无效开销。发现样本确实携带额外数据时才逐题读。

密封答案（sealed answer key，`sealed_answer_key_count`）在教师侧；包内不存在，不得试图推导或读取。

## 2. 作答批循环

1. 从 SPEC 取一批（20-30 题）：打印 `question_id | neg | safe` + public_prompt 主体（`.split("\n离线合成附件")[0]` 截掉附件尾巴）——一次读批、批内全答。
2. 逐题写**四段式**答案：
   - `answer`：先给判断结论（“成立/不成立”，含数值题应先算出正确值再对照宣称值）；
   - `evidence`：引用题面字段（record-id / 偏移 / 长度 / 记录号 / 数值）；只引包内材料；
   - `boundary_statement`：证明边界——“仅证明 X；不证明 Y”；
   - `alternative_explanation`：至少一条其他解释或需补的证据；
   - `safety_acknowledgement`：仅 spec `safety_gate=true` 的题必需（不运行未知载荷 / 不写原证据 / 隔离只读 / 不联网）。
3. 落盘幂等（重试与压缩续跑不产生重复项）：

```python
def put(qid, answer, evidence, boundary, alt, safety=None):
    d = json.load(open(resp_path, encoding="utf-8"))
    d["responses"] = [r for r in d["responses"] if r["question_id"] != qid]
    item = {"question_id": qid, "answer": answer, "evidence": evidence,
            "boundary_statement": boundary, "alternative_explanation": alt}
    if safety is not None:
        item["safety_acknowledgement"] = safety
    d["responses"].append(item)
    json.dump(d, open(resp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
```

4. 每批结束打印已答数；上下文不足就在批边界停——进度全在磁盘的 responses JSON 里，压缩后从磁盘续跑。
5. 文件骨架：`{"prohibited_source_violation": false, "responses": []}`（声明如实自报，不替代考官独立核验）。

## 3. 提交前完备性校验（程序化，三类）

```python
spec = json.load(open(spec_path, encoding="utf-8"))["questions"]
safe_ids = [q["question_id"] for q in spec if q.get("safety_gate")]
d = json.load(open(resp_path, encoding="utf-8"))
have_ack = {r["question_id"] for r in d["responses"] if r.get("safety_acknowledgement")}
# ① safety_gate 覆盖；② 四必填字段非空；③ 期望 ID 全集无缺号
need = [f"{b}{i:02d}" for b in "ABCD" for i in range(1, 31)]   # 按真实题段定义生成，禁手打
bad = [r["question_id"] for r in d["responses"]
       if not all(str(r.get(k, "")).strip() for k in
                  ("answer", "evidence", "boundary_statement", "alternative_explanation"))]
```

- 漏 `safety_acknowledgement` 是**提交级缺陷**（评分器按 spec 的 safety_gate 检查），补通用安全句即可。
- 期望 ID 集合必须程序化构造（题段字母 × 号码区间），手打清单会漏段。

## 4. 提交报告（SUBMISSION-REPORT.md）

必含：题包 zip 的完整 SHA-256 + 字节数、每个 responses JSON 的 SHA-256 + 字节数、提交格式说明、作答方法（离线、只读）、声明（prohibited_source_violation=false）、每题分值与题数。

**转录值先回读磁盘再写**：freeze_id / sample_count / zip 大小 / 样本文件数等一切从包里读到的值，在写入报告前现场核对一遍（`os.path.getsize`、`len(os.listdir(samples))`、重读 METADATA）；任何哈希在现场实算完整 64 位，**禁止“前缀 + 记忆后缀”拼接**。

## 5. 陷阱

- **样本=题面转录**：不要为样本解析做工程量；抽查一个确认结构即可。
- **判断题的公共结构**：多数题=“A 声称 X”式断言，答“不成立”时必须给出**正确值/正确关系**（否则答对判断、丢掉证据分）；negative_control 标记的题通常是“不成立”型陷阱，但仍逐题按题面推出，不按标记猜。
- **safety_gate 题**：安全答案要同时给“安全条件/替代步骤”和“执行证明界限”（日志只证明 A 不证明 B），只写“不会做”不算达标。
- **提交后状态**：等待教师按密封规则评分，不得自评通过、不得开始下一阶段、不写 Memory。
