# 2024 数证杯第一跳与复测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 2024 数证杯每道题的第一个取证工具调用来自现有路由表，并用一题一进程的占用时间在做过的卷上复测。

**Architecture:** `dfir_router.py` 导出 `route(text) -> dict`，钩子和 `dfir-solve.ps1` 共用。匹配到的题把命令写进单题 prompt；匹配不到的题 prompt 保持原样。评分仍走 `eval_gold.py`，金标放在模型 `--in` 目录之外。速度旋钮（削提示、改 plain）本计划不实现。

**Tech Stack:** Python 3.12（`C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe`）、Windows PowerShell 5.1、现有 `dfir-solve.ps1` / llama.cpp 栈。不新增依赖。

**Spec:** `C:\Users\TWK\orca\workspaces\ForensicsAgent\加速\docs\superpowers\specs\2026-11-11-local-forensics-upgrade-design.md`

## Global Constraints

- 实现只改 `D:\ForensicsAgent\hermes\`。不要改工作区 `C:\Users\TWK\orca\workspaces\ForensicsAgent\加速` 里的旧 profile 副本。
- 不改 `SOUL.md`。`dfir-myos` 与 `dfir-max` 的 `ios-backup-ctf/SKILL.md`、`windows-computer-paper.md` 哈希已相同（`24bd742dfe21`、`ec3ec120d577`），不要互相覆盖，也不要覆盖两份不同的 SOUL。
- 不改 `D:\llm\server-config.json`，不改 `-c 65536`，不关 MTP，不上 DFlash2，不加大 `--cache-ram`。
- 金标、本计划、技能、SOUL、`D:\forensics\cases\notes\` 都不写入题解答案字符串。
- 金标路径必须在 `D:\forensics\cases` 之外。模型 prompt 不出现 `gold-2024` 或 `hermes\state\eval`。
- 2024 题全部用基础预算 12 次 / 480 秒。不写 `complex-questions` 侧车。允许脚本既有的一次 6/240 重试。单题日志秒数（含这一次重试）超过 720，或状态为 `TIMEOUT`，判时间失败。
- 整卷占用：手机 ≤ 2700 秒，计算机 ≤ 3600 秒。
- 错答为 0。UNKNOWN / 未取到 / 待确认 不是错答。
- 手机必对：1、3、4、5、6、7、8。题 2 只要求不是 WRONG。计算机必对：1、2、6、7、8、9、10。题 3 允许 OK 或 UNKNOWN。题 4、题 5 不设必对。
- 第一个取证工具调用之前，只允许读本题索引：手机 `device_map.myos.summary.txt`，计算机 `device_map.computer.summary.txt`。不要先 `skill_view`，不要先全盘 `ls`。
- 案件打不开就停。不新建取证任务，不 `restart_computer_forensics`。
- 提交只 `git add` 本任务列出的路径。`D:\ForensicsAgent` 的 master 上已有无关改动，不要带上。
- 阶段 2（削提示、`local-plain` 对照）不在本计划内。复测没过 3 万 token 或 thinking 占比时，停下来另写计划。

## Review Focus

- 题面只有「手机取证」、没有 iOS 词时，仍路由到 `mobile-ctf-pipeline`，且没有第一跳。误判会让普通安卓题被塞进 iOS 探针。
- 题面有「远程连接」、没有「向日葵」时，命令是 `Win_RemoteDesktopInfo`，禁止列才出现向日葵。命令本身带向日葵会重演 7 分钟空翻日志。
- 题面同时有「发送」「照片」「GPS」时，第一跳是附件 EXIF，不是 `trailer`，也不是 OCR。
- 金标若放进 `notes\`，评分程序必须拒绝并在打印任何答案之前退出。
- 不带 `-QuestionsFile` 时，题号 1–8 仍自动选中现有的 `questions-1-8.txt`（2025 卷）。2024 题面文件名不得匹配 `questions-(\d+)-(\d+)\.txt`。

## File structure

- `D:\ForensicsAgent\hermes\bin\questions_to_pipe.py` — 把桌面题面收成 `N|单行`。
- `D:\ForensicsAgent\hermes\bin\eval_gold.py` — 增加错答计数、金标路径拒绝、`paper_gate`。
- `D:\ForensicsAgent\hermes\bin\occupied_time.py` — 长会话空档对照，不作为通过条件。
- `D:\ForensicsAgent\hermes\bin\ios_backup_probe.py` — 增加只读 `sum-by-uuid`。
- `D:\ForensicsAgent\hermes\bin\dfir_router.py` — `route()` 与 `--route`。
- `D:\ForensicsAgent\hermes\bin\dfir-solve.ps1` — 单题 prompt 插入第一跳；DryRun 打印它。
- `D:\ForensicsAgent\hermes\bin\tests\test_route.py` — 路由器与门禁的失败测试。
- `D:\forensics\cases\notes\questions-2024szb-mobile.txt` 与 `questions-2024szb-computer.txt` — 转换后的题面，不是金标。
- `D:\ForensicsAgent\hermes\state\eval\gold-2024szb-mobile.json` 与 `gold-2024szb-computer.json` — 金标，实现者从既有复盘填，本计划不写答案。

---

### Task 1: 题面收成单行，且不会被自动选中

**Files:**
- Create: `D:\ForensicsAgent\hermes\bin\questions_to_pipe.py`
- Create: `D:\ForensicsAgent\hermes\bin\tests\test_questions_to_pipe.py`
- Create: `D:\forensics\cases\notes\questions-2024szb-mobile.txt`
- Create: `D:\forensics\cases\notes\questions-2024szb-computer.txt`

**Interfaces:**
- Consumes: 无
- Produces: `to_pipe_lines(text: str) -> list[str]`，元素形如 `1|...`。编号行匹配 `^\d+[.|、]`，其后的非编号行并入上一题。完全没有编号时，每个非空行按出现顺序编号。CLI 是 `questions_to_pipe.py infile outfile`，写出这些行。

- [ ] **Step 1: 在 `D:\ForensicsAgent` 建分支**

```powershell
git -C D:\ForensicsAgent switch -c upgrade-2024szb-first-jump
```

不要 `git add` 已有的无关改动。

- [ ] **Step 2: 写失败测试**

`test_numbered_continuation_joins`：输入 `"3.去过\n\nA: 甲\n\n4.下一题"`，断言得到两行，第一行以 `3|` 开头且同时含 `去过` 和 `A: 甲`。

`test_unnumbered_lines_are_ordered`：输入 `"第一题\n第二题\n"`，断言 `["1|第一题", "2|第二题"]`。

`test_2024_names_do_not_match_range_autoselect`：对文件名 `questions-2024szb-mobile.txt` 断言 `re.match(r'^questions-(\d+)-(\d+)\.txt$', name)` 为 None。在同时放有 `questions-1-8.txt`（内容 `1|old`）和 `questions-2024szb-mobile.txt` 的临时 notes 目录上调用 `dfir_plan.select_question_file(notes, [1, 2, 8])`，断言选中的是 `questions-1-8.txt`。

- [ ] **Step 3: 跑测试，确认失败**

Run: `C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe -m pytest D:\ForensicsAgent\hermes\bin\tests\test_questions_to_pipe.py -v`

Expected: FAIL，`to_pipe_lines` 不存在。pytest 不在时用 `python -m unittest` 跑同一个文件，预期同样是 import/attribute 失败。

- [ ] **Step 4: 实现 `to_pipe_lines`**

只做接口里写的两种切分。不要读取桌面题面，不要写答案。

- [ ] **Step 5: 转换两份真题面并核对行数**

Run:

```powershell
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe D:\ForensicsAgent\hermes\bin\questions_to_pipe.py D:\Desktop\手机取证.txt D:\forensics\cases\notes\questions-2024szb-mobile.txt
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe D:\ForensicsAgent\hermes\bin\questions_to_pipe.py D:\Desktop\计算机取证.txt D:\forensics\cases\notes\questions-2024szb-computer.txt
```

`questions_to_pipe.py` 的 CLI 是 `infile outfile`，内部调用 `to_pipe_lines`。转换后手机文件 8 行、计算机文件 10 行，每行匹配 `^\d+\|`。手机第 3 行含选项字母 `A:`。不要把这两份文件的正文贴进提交说明。

- [ ] **Step 6: 测试通过**

同一条 pytest 命令。Expected: PASS。

- [ ] **Step 7: Commit**

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/questions_to_pipe.py hermes/bin/tests/test_questions_to_pipe.py
git -C D:\ForensicsAgent commit -m "feat: convert contest stems to pipe lines without taking the 1-8 slot"
```

题面 txt 在 `D:\forensics\cases`，不在这个 git 仓库里，不要 add。提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

### Task 2: 金标路径拒绝与卷面门禁

**Files:**
- Modify: `D:\ForensicsAgent\hermes\bin\eval_gold.py`
- Create: `D:\ForensicsAgent\hermes\bin\tests\test_eval_gate.py`
- Create: `D:\ForensicsAgent\hermes\state\eval\gold-2024szb-mobile.json`
- Create: `D:\ForensicsAgent\hermes\state\eval\gold-2024szb-computer.json`

**Interfaces:**
- Consumes: 现有 `read_answer`、`match`、`read_timings`。日志行格式已是 `Q11 | profile | 320s | OK | attempt=1 | 时间戳`。
- Produces:
  - `gold_path_allowed(gold: Path) -> bool`。`gold` 解析后位于 `D:\forensics\cases` 之内则 False。
  - `paper_gate(summary: dict, paper: str) -> list[str]`。`summary` 沿用 `main()` 现有键，并增加 `wrong`。`paper` 为 `mobile` 或 `computer`。返回失败原因列表，空列表为通过。
  - 门禁数字用 Global Constraints 里的题号、720 秒、2700 秒、3600 秒。`seconds is None` 算失败。`TIMEOUT` 算失败。题 2 的 WRONG 算失败，UNKNOWN 不算。题 3 计算机的 UNKNOWN 不算失败。

- [ ] **Step 1: 写失败测试**

用临时目录和假答案，不要读真金标。

`test_gold_inside_notes_is_rejected`：`gold_path_allowed(Path(r"D:\forensics\cases\notes\gold.json"))` 为 False。`main()` 在该路径上返回 2，且 stdout 不含假答案 `SECRET-ANSWER`。做法：把这个断言做成对 `gold_path_allowed` 的直接调用；另写一个子进程测试，仅当实现把拒绝放在读文件之后才需要假文件。拒绝必须发生在打印表格之前。

`test_wrong_is_not_unknown`：pending 写 `答案：1200元`，金标 `accept` 为 `["1300元"]`，`paper_gate` 的失败列表含 WRONG，且不把该题记成 UNKNOWN。

`test_mobile_gate_numbers`：构造 summary，题 1、3、4、5、6、7、8 为 OK 且 seconds=100，题 2 为 UNKNOWN 且 seconds=100，`wrong` 为 0，`elapsed_seconds` 为 800。`paper_gate(..., "mobile")` 为空。把题 3 改成 UNKNOWN 后，列表非空。

`test_computer_q3_unknown_allowed`：题 1、2、6、7、8、9、10 为 OK，题 3、4、5 为 UNKNOWN，每题 100 秒。`paper_gate(..., "computer")` 为空。题 6 改为 WRONG 后非空。

- [ ] **Step 2: 跑测试，确认失败**

Run: `C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe -m pytest D:\ForensicsAgent\hermes\bin\tests\test_eval_gate.py -v`

Expected: FAIL，`paper_gate` 不存在。

- [ ] **Step 3: 实现拒绝与门禁**

`main()` 在 `json.loads` 之前调用 `gold_path_allowed`。不允许则打印 `gold 不在允许路径` 到 stderr 并返回 2。summary 增加 `wrong`，等于 verdict 为 WRONG 的行数。不要改 11–20 的默认金标路径。

- [ ] **Step 4: 填两份真金标**

来源只读已有复盘，不要把读到的答案写进计划、技能或 notes，也不要从模型会话记录里反推：

- `C:\Users\TWK\.claude\projects\D--ForensicsAgent\memory\2024-shuzhengbei-mobile-lessons-2026-11-10.md`
- `C:\Users\TWK\.claude\projects\D--ForensicsAgent\memory\2024-shuzhengbei-computer-lessons-2026-11-11.md`
- 计算机复盘里点名的四份题解（WXjzc、CSDN 2301_80727080、zzpu213、CSDN qq_43491969），只在本地找得到时读

必对题的 `accept` 填不上就停下来问，不要编。

JSON 形状与 `gold-11-20.json` 相同：顶层 `questions`，键为题号字符串，每题有 `answer`、`accept`、`verified`。没有复盘结论的计算机题 4 和题 5，`answer` 置空字符串，`accept` 置空数组，`verified` 为 false。`paper_gate` 不读这两题的答案。

写完后跑一个只打印题号和 `accept` 是否非空的检查，不打印 `answer`。手机 1–8 除了不存在的空题外，`accept` 非空。计算机 1、2、3、6、7、8、9、10 的 `accept` 非空；4 和 5 为空。

- [ ] **Step 5: 测试通过并提交**

同一条 pytest。Expected: PASS。

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/eval_gold.py hermes/bin/tests/test_eval_gate.py hermes/state/eval/gold-2024szb-mobile.json hermes/state/eval/gold-2024szb-computer.json
git -C D:\ForensicsAgent commit -m "feat: reject in-notes gold and gate 2024 papers separately"
```

提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

### Task 3: 长会话空档对照

**Files:**
- Create: `D:\ForensicsAgent\hermes\bin\occupied_time.py`
- Create: `D:\ForensicsAgent\hermes\bin\tests\test_occupied_time.py`

**Interfaces:**
- Consumes: 无
- Produces: `user_idle_seconds(messages: list[tuple[float, str]], gap: float = 300) -> float`。`messages` 为 `(timestamp, role)`，按时间已排序。只累加大于 `gap` 且下一条 `role=="user"` 的间隔。等于 300 不累加。

- [ ] **Step 1: 写失败测试**

`test_user_gap_over_five_minutes_counts`：`(0, "assistant")` 到 `(301, "user")` 得 301。

`test_tool_gap_does_not_count`：`(0, "assistant")` 到 `(400, "tool")` 得 0。

`test_five_minutes_exact_does_not_count`：间隔正好 300、下一条 user，得 0。

- [ ] **Step 2: 跑测试，确认失败**

Expected: FAIL，函数不存在。

- [ ] **Step 3: 实现函数**

CLI 可以读 `state.db`，但测试只调函数，不打开真库。这是对照工具，复测通过条件不调用它。

- [ ] **Step 4: 测试通过并提交**

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/occupied_time.py hermes/bin/tests/test_occupied_time.py
git -C D:\ForensicsAgent commit -m "feat: measure user idle gaps without using them as the gate"
```

提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

### Task 4: 按 uuid 求和，禁止 DISTINCT

**Files:**
- Modify: `D:\ForensicsAgent\hermes\bin\ios_backup_probe.py`
- Create: `D:\ForensicsAgent\hermes\bin\tests\test_sum_by_uuid.py`

**Interfaces:**
- Consumes: 无
- Produces: `sum_by_uuid(path: str, table: str, id_column: str, amount_column: str) -> None`。只读打开 sqlite。同一 id 只加一次。不同 id 的相同金额都加。打印每行 `id\tamount`，最后一行 `SUM <整数>`。CLI：`ios_backup_probe.py sum-by-uuid <sqlite> <表> <id列> <金额列>`。

- [ ] **Step 1: 写失败测试**

临时 sqlite，表 `t(id TEXT, money INTEGER)`，两行 id 不同、money 都是 10000，一行重复 id。断言 stdout 含 `SUM 20000`，且不含 `SUM 10000`。

- [ ] **Step 2: 跑测试，确认失败**

Expected: FAIL，用法字符串仍只有 `districts` 和 `trailer`。

- [ ] **Step 3: 实现**

SQL 按 id 分组后把每组的一笔金额相加，不要 `SUM(DISTINCT money)`。列名只允许 `[A-Za-z0-9_]`，否则 `fail`。不要写金标金额。

- [ ] **Step 4: 测试通过并提交**

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/ios_backup_probe.py hermes/bin/tests/test_sum_by_uuid.py
git -C D:\ForensicsAgent commit -m "feat: sum ledger rows by uuid instead of distinct amount"
```

提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

### Task 5: 路由器输出第一跳

**Files:**
- Modify: `D:\ForensicsAgent\hermes\bin\dfir_router.py`
- Create: `D:\ForensicsAgent\hermes\bin\tests\test_route.py`
- Backup: `D:\ForensicsAgent\hermes\profiles\.backup-20261111-upgrade\dfir_router.py`

**Interfaces:**
- Consumes: Task 4 的 CLI 字符串
- Produces: `route(text: str) -> dict`，键为 `skill`、`command`、`forbid`、`index_file`，类型都是 `str | None`。`format_first_jump_block(jump: dict) -> str`。无命令时 `format_first_jump_block` 返回空字符串。

CLI：`python dfir_router.py --route`，从 stdin 读题面，打印 `route()` 的 JSON。无匹配时四个键都是 null。

钩子路径仍读 stdin JSON。`local_skill` 在现有分支之前先看 `route(text)["skill"]`。有 `command` 时，`context` 使用 `format_first_jump_block` 的原文，并写明不要在该命令之前 `skill_view`。

匹配顺序，先命中先返回。计算机标记词：`BitLocker`、`恢复密钥`、`远程连接`、`远程桌面`、`vhd`、`VHD`、`VeraCrypt`、`torrent`、`onion`、`Tor`、`回收站`、`删除时间`、`4625`、`登录失败`、`发件人`、`附件`、`GPS`。有任一标记才走计算机规则，否则走 iOS 规则。

计算机规则按此顺序：

| 题面含 | command 必须含 | forbid 必须含 | skill | index_file |
|---|---|---|---|---|
| `GPS` 且 `照片` | `PIL` 和 `EXIF` | `Any_ImageExifInfo` | `myos-results-analysis` | `device_map.computer.summary.txt` |
| `BitLocker` 或 `恢复密钥` | `Win_BitlockerRecoveryKey.mfs` | `GUID` | 同上 | 同上 |
| `远程连接` 或 `远程桌面` | `Win_RemoteDesktopInfo` | `向日葵` | 同上 | 同上 |
| `vhd` 或 `VHD` | `Mount-Vhd` | `手解` 和 `BAT` | 同上 | 同上 |
| `torrent` 或 `onion` 或 `Tor` | `places.sqlite` | `Chrome` | 同上 | 同上 |
| `删除时间` 或 `回收站` | `$I` | `零命中` | 同上 | 同上 |
| `登录失败` 或 `4625` | `POST_DATA` | `ACCOUNT_NAME` | 同上 | 同上 |
| `发件人` 或 `附件` | `Any_SingleMail` 和 `FILE_MD5` | `PST` | 同上 | 同上 |

iOS 规则按此顺序：

| 题面含 | command 必须含 | forbid 必须含 | skill | index_file |
|---|---|---|---|---|
| `家庭地址` | `TBL_PR_GAODEMAP_GEO_ADDRESS_COLLECT` | `通讯录` | `ios-backup-ctf` | `device_map.myos.summary.txt` |
| `去过` 或 `区县` | `ios_backup_probe.py districts` | `ZLOCATIONDATA` | 同上 | 同上 |
| `单价` 或 `大麻` 或 `图片` | `ios_backup_probe.py trailer` | `D0CF11E0` | 同上 | 同上 |
| `礼金` 或 `记账` | `sum-by-uuid` | `SUM(DISTINCT` | 同上 | 同上 |
| `facebook` 或 `钥匙串` 或 `网站密码` | `UNKNOWN` | `keybag` | 同上 | 同上 |

`序列号`、`备份密码`、`Platform/DeviceInfo` 不产生 command。`route()` 的 `skill` 仍为 `ios-backup-ctf`，其余三键为 null。这样不发明第一跳，但钩子不会把它送去 `mobile-ctf-pipeline`。

`format_first_jump_block` 在 command 非空时返回这段，花括号是字段值：

```text
第一跳（本轮第一个取证工具调用必须是下面这条；在此之前只允许读本题索引文件 {index_file}，不要 skill_view，不要 ls 全盘）：
{command}
禁止：{forbid}
```

- [ ] **Step 1: 备份路由器**

```powershell
New-Item -ItemType Directory -Force -Path D:\ForensicsAgent\hermes\profiles\.backup-20261111-upgrade
Copy-Item D:\ForensicsAgent\hermes\bin\dfir_router.py D:\ForensicsAgent\hermes\profiles\.backup-20261111-upgrade\dfir_router.py
```

- [ ] **Step 2: 写失败测试**

`test_plain_mobile_is_not_ios`：`route("请做手机取证")` 四键都是 null。现有 `local_skill("请做手机取证")` 仍返回 `mobile-ctf-pipeline`。

`test_remote_without_sunflower`：题面 `曾远程连接过该计算机的 IP`。command 含 `Win_RemoteDesktopInfo`，不含 `向日葵`。forbid 含 `向日葵`。

`test_email_photo_is_exif_not_trailer`：题面 `曾经发送过一张照片，写出 GPS`。command 含 `EXIF`，不含 `trailer`，不含 `ocr`。

`test_unit_price_is_trailer`：题面 `走私物品的单价是每克多少元`。command 含 `trailer`，forbid 含 `D0CF11E0`。

`test_serial_has_skill_but_no_command`：题面 `写出苹果手机的序列号`。skill 为 `ios-backup-ctf`，command 为 None。

`test_block_names_index_and_omits_gold`：家庭地址题的 block 含 `device_map.myos.summary.txt`，不含 `gold-2024`，不含 `state\eval`。无 command 时 block 为 `""`。

- [ ] **Step 3: 跑测试，确认失败**

Expected: FAIL，`route` 不存在。

- [ ] **Step 4: 实现 `route`、`format_first_jump_block`、`--route`**

命令句子用上表的必须含有的子串，路径占位留给模型从索引填。不要把金标或答案写进命令。钩子在 `route()` 给出 skill 时用该 skill，不再落到后面的 `mobile-ctf-pipeline`。

- [ ] **Step 5: 测试通过并提交**

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/dfir_router.py hermes/bin/tests/test_route.py
git -C D:\ForensicsAgent commit -m "feat: route contest stems to a first evidence command"
```

提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。备份目录不必提交。

### Task 6: 单题 prompt 带上第一跳

**Files:**
- Modify: `D:\ForensicsAgent\hermes\bin\dfir-solve.ps1` 的 `Get-SkillsForDomain`、`New-Prompt`、DryRun 分支（约 164–176、189–302、503–508 行）

**Interfaces:**
- Consumes: `python dfir_router.py --route` 的 JSON。Python 用脚本里已有的 `$python`（3.12）。题面经 stdin 传入，不要拼进命令行。
- Produces: DryRun 的主机输出行含 `first=<command 或 none>`。`New-Prompt` 在题面之后、硬性步骤之前插入 `format_first_jump_block` 的原文；空字符串时不插入。iOS skill 非空时，`-s` 技能列表以 `ios-backup-ctf` 开头，后面仍保留原来的 `android-app-forensics,mobile-ctf-pipeline`。

- [ ] **Step 1: 写失败检查所用的临时案件**

在临时目录建 `notes\questions-2024szb-mobile.txt`，一行：`3|分析手机检材，哪些地址是曾经去过的`。不要用真案件目录。

- [ ] **Step 2: DryRun，确认现在没有 first=**

```powershell
powershell -File D:\ForensicsAgent\hermes\bin\dfir-solve.ps1 -Questions 3 -QuestionsFile <临时文件> -CaseRoot <临时根> -Domain mobile -DryRun
```

Expected: 输出没有 `first=`。这是改之前的基线。

- [ ] **Step 3: 把 `--route` 的结果插入 prompt**

PowerShell 5.1 没有 `&&`。stdin 用 here-string 管道。解析 JSON 用 `$python -c` 打印四个字段，或 `ConvertFrom-Json`。command 为 null 时 DryRun 打印 `first=none`。

隔离规则那段原文保留，包括「禁止读 … 任何 gold/eval/参考答案」。不要把金标路径补进 prompt。

- [ ] **Step 4: 再跑 DryRun**

同一命令。Expected: 输出含 `first=` 且含 `districts`，含 `ios-backup-ctf`，不含 `gold-2024`。

另建一行题面 `1|请做手机取证`，用 `-Questions 1 -QuestionsFile` 再 DryRun。Expected: `first=none`，技能列表不含 `ios-backup-ctf`。不要把这句话当 `-Questions` 参数。

- [ ] **Step 5: Commit**

```powershell
git -C D:\ForensicsAgent add -- hermes/bin/dfir-solve.ps1
git -C D:\ForensicsAgent commit -m "feat: put the routed first command into the per-question prompt"
```

提交说明末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

### Task 7: 旧 mock 不回退

**Files:**
- Test: `D:\ForensicsAgent\benchmarks\mock\run_mock.py`
- Test: Task 1、2、4、5 的测试文件

- [ ] **Step 1: 跑路由器测试和 mock**

```powershell
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe -m pytest D:\ForensicsAgent\hermes\bin\tests -v
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe D:\ForensicsAgent\benchmarks\mock\run_mock.py
```

Expected: pytest 全过。`run_mock.py` 的 JSON 里 `"ok": true`。失败则停，不要进入 Task 8。

- [ ] **Step 2: 不提交**

这一任务只验证，没有新文件。

### Task 8: 备份旧 pending，再跑两套卷

**Files:**
- Backup: `D:\ForensicsAgent\hermes\state\eval\backup-pending-20261111\`
- Reads: `D:\forensics\cases\notes\pending-1.md` 到 `pending-10.md`，以及 `_solve.log`
- Does not modify: 服务器配置、SOUL、技能正文

**Interfaces:**
- Consumes: Task 2 的两份金标和 `paper_gate`。Task 6 的 `dfir-solve.ps1`。
- Produces: `eval_gold.py` 写出的 `hermes\state\eval_runs\<时间戳>.json`。通过条件是 `paper_gate` 返回空列表，且图片/单价题的第一次取证工具是 `trailer`，`.mfs` 题的前 3 次取证工具里有 `sqlite_query`。

- [ ] **Step 1: 确认案件还开着**

读 `D:\forensics\cases\notes\device_map.myos.summary.txt` 和 `device_map.computer.summary.txt` 的赛名。对不上 2024 数证杯，或文件不存在，就停。不要调用 `restart_computer_forensics`，不要 `load_case` 去修评测。

- [ ] **Step 2: 备份将被覆盖的 pending**

```powershell
New-Item -ItemType Directory -Force -Path D:\ForensicsAgent\hermes\state\eval\backup-pending-20261111
Copy-Item D:\forensics\cases\notes\pending-*.md D:\ForensicsAgent\hermes\state\eval\backup-pending-20261111\
Copy-Item D:\forensics\cases\notes\_solve.log D:\ForensicsAgent\hermes\state\eval\backup-pending-20261111\
```

`pending-*.md` 不存在就跳过该文件，不要中断。

- [ ] **Step 3: 先手机，后计算机**

必须带 `-QuestionsFile` 和 `-SkipEvalGold`。不带的话，1–8 会跑到 2025 的 `questions-1-8.txt`，结束时还会用 `gold-11-20.json` 打分。

```powershell
powershell -File D:\ForensicsAgent\hermes\bin\dfir-solve.ps1 -Questions 1-8 -QuestionsFile D:\forensics\cases\notes\questions-2024szb-mobile.txt -Domain mobile -SkipEvalGold
powershell -File D:\ForensicsAgent\hermes\bin\dfir-solve.ps1 -Questions 1-10 -QuestionsFile D:\forensics\cases\notes\questions-2024szb-computer.txt -Domain computer -SkipEvalGold
```

不要恢复 2026-11-10/11 的长会话。这是新的 `hermes chat --oneshot`，不依赖正在跑的 gateway 热加载。

- [ ] **Step 4: 评分**

```powershell
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe D:\ForensicsAgent\hermes\bin\eval_gold.py --gold D:\ForensicsAgent\hermes\state\eval\gold-2024szb-mobile.json --questions 1,2,3,4,5,6,7,8
C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe D:\ForensicsAgent\hermes\bin\eval_gold.py --gold D:\ForensicsAgent\hermes\state\eval\gold-2024szb-computer.json --questions 1,2,3,4,5,6,7,8,9,10
```

对两份新写出的 eval JSON 调用 `paper_gate`。空列表才算过。

另读每题的 `notes\_solve-q<N>-a*.log`。单价题（手机 8）第一次取证工具不是 `trailer`，或邮件/登录失败/回收站题的前 3 次取证工具没有 `sqlite_query`，记 Task 5/6 失败，即使答案碰巧对。日志里的工具名格式先看一份现有 `_solve-q*.log` 再解析，不要猜字段名。

单题 prompt 的输入 token 从该题 hermes 日志或 llama-server 的本次请求读取。任一请求超过 30000，停，不要削提示，不要改窗口。那是下一份计划。

- [ ] **Step 5: 没过就停在失败题上**

只改 `route()` 的对应行或停止句，不把金标句子写进技能。改完只重跑失败题和一道已通过的邻题。邻题回退则还原该行。

不要在这一任务里改 `model.provider`。

- [ ] **Step 6: 不把 pending 答案提交进 git**

`D:\forensics\cases\notes` 不在仓库里。仓库里只应已有 Task 1–6 的提交。本任务没有新的源码提交，除非 Step 5 改了 `dfir_router.py`。那种提交只 add 该文件。
