# 配置差异草案（未应用）

日期：2026-10-30（Asia/Shanghai）
生产配置：`D:\llm\server-config.json`
启动入口：计划任务 `llama-server-8095`；不要直接双击 exe。
约束：保持 `-c 65536`、主模型与 IQ3-MIX 权重、`reasoning on`、`--reasoning-budget 2048`、K/V 均 `q8_0`、`-np 1`。本文件只是草案，未修改生产配置。

## 0. 当前配置（已核实）

关键片段：

```json
"-c", "65536",
"-np", "1",
"-ngl", "64",
"-b", "512",
"-ub", "128",
"-t", "6",
"-tb", "6",
"--fit", "off",
"--flash-attn", "on",
"--cache-type-k", "q8_0",
"--cache-type-v", "q8_0",
"--kv-unified",
"--cache-ram", "512",
"--reasoning", "on",
"--reasoning-format", "deepseek",
"--reasoning-budget", "2048"
```

运行进程命令行与上述一致（PID 41580，父进程 pythonw.exe，计划任务 llama-server-8095）。

## 1. Stage A：释放显存 + 完整 GPU 卸载（第一优先）

### 1.1 先释放其他 GPU 进程（不改服务配置）

本机实测的专用显存占用（Windows GPU Process Memory 计数器，2026-10-30 21:0x）：

| PID | 进程 | Dedicated |
|---|---|---:|
| 41580 | llama-server.exe | 14,484,697,088 B（13.49 GiB） |
| 24272 | dwm.exe（系统桌面合成） | 721,219,584 B |
| 44532 | explorer.exe（系统外壳） | 430,268,416 B |
| 18548 | Trae CN | 368,201,728 B |
| 43324 | ChatGPT | 106,897,408 B |
| 46788 | WindowsTerminal | 105,918,464 B |
| 15696 | GoldenEyesV4 | 96,309,248 B |
| 43076 | ZCode | 79,388,672 B |
| 42664/32272/6604 | Edge/WebView2 | 约 156 MB |
| 2548 | SnippingTool | 34,369,536 B |

不建议关闭 `dwm`、`explorer`、`csrss` 等系统组件；可临时关闭的用户态应用约 0.9 GiB。当前空闲可用显存约 386 MiB（`nvidia-smi` 15,618/16,303 MiB 已用）。只有先释放约 0.9–1.2 GiB，Stage A/B 才有稳定余量。
本机只枚举到一个可用显示适配器（NVIDIA）；AMD Radeon 610M 的 PnP 状态为 Unknown/未启动，不能假设现在可以把桌面或应用分流到 iGPU。启用 iGPU 属于 BIOS/驱动变更，不作为第一方案。

### 1.2 只改一个参数：`-ngl`

```diff
-    "-ngl",
-    "64",
+    "-ngl",
+    "all",
```

`-ngl all` 在该版本解析为 `-2`，`n_gpu_layers()` 对任何负数返回 `n_layer_all + 1`，本模型为 65 + 1 = 66 个卸载槽（`common/arg.cpp:2805-2812`，`src/llama-model.cpp:2418-2421`）。66 个槽 = 64 个主干块 + 1 个 MTP 占位块 + 输出层。MTP 未启用时块 64 没有加载张量，因此实际效果是把 `blk.0`、`blk.1` 两个主干块从 CPU 移到 GPU，输出层本来就在 GPU。

显存增量：`340,637,952 B = 324.9 MiB`（两个 block 各 170,318,976 B）。
预期：消除每个 token 的 CPU→GPU 串行等待；短/中上下文解码有望提升约 5–20%（估算，未测）；56K 提升可能较小。
回滚：把 `"all"` 改回 `"64"`，停止并重启计划任务。

### 1.3 备选：`-ngl 65`

如果 `-ngl all` 在 64K 下 OOM 或出现持续共享显存增长，可只移 `blk.1`，保留 `blk.0` 在 CPU：

```diff
-    "64",
+    "65",
```

显存增量约 162.4 MiB；速度增益小于 `all`，但比当前好。它是 Stage A 的降级路径，不是最终目标。

## 2. Stage B：原生 MTP（在 Stage A 通过后）

### 2.1 最小改动

```diff
     "--reasoning-budget",
-    "2048"
+    "2048",
+    "--spec-type",
+    "draft-mtp",
+    "--spec-draft-n-max",
+    "1",
+    "--spec-draft-type-k",
+    "q8_0",
+    "--spec-draft-type-v",
+    "q8_0"
```

不要加 `-md`/`--model-draft`：该版本在 `spec_mtp` 且没有外部 draft 时，用目标模型创建 MTP context（`common/speculative.cpp:2680-2705`）。启动时 `load_mtp` 会被置为 true（`common/common.cpp:1706`），因此 `blk.64.*` 不再被当作 unused tensor，MTP 权重约 227.9 MiB 会加载。MTP 权重随 `-ngl` 放置；`-ngl all` 或 64 时块 64 都在 GPU。

**草稿 KV 类型必须显式指定。** `common_params_speculative_draft.cache_type_k/v` 默认 F16（`common/common.h:348-349`），`common_base_params_to_speculative` 会把该值复制给草稿 context 的 `cache_type_k/v`（`common/speculative.cpp:2600-2601`）。MTP context 按完整 65,536 分配，F16 单层 KV 为 256.0 MiB；加 `--spec-draft-type-k q8_0 --spec-draft-type-v q8_0` 后为 136.0 MiB。这不改变主模型 K/V 的 q8_0，也不违反“主模型 K/V q8”的约束；它只影响草稿 context 的显存和接受率。F16 草稿可作为单独对照，需额外约 120 MiB 显存。

如果 A+B 在 64K OOM，按顺序降级（不要缩上下文/降主模型 KV）：
1. `-ngl 65` + MTP q8：A 增量 162.4MiB，A+B 约 0.63–0.78GiB；
2. `-ngl 64` + MTP q8：A 增量 0，B 约 0.46–0.61GiB；
3. 再关闭更多用户态 GPU 应用（保留 dwm/explorer/csrss）。
这些档位都要单独跑，不能把 ngl64+MTP 的结果外推到 ngl all+MTP。

### 2.2 草稿长度测试顺序

1. `--spec-draft-n-max 1`
2. `--spec-draft-n-max 2`
3. `--spec-draft-n-max 3`（默认值就是 3，但必须显式记录）

每次只改这一个值。若显存紧张，先加：

```diff
+    "--spec-draft-n-ubatch",
+    "1"
```

这会降低 MTP 草稿图的物理批大小，可能牺牲草稿速度但减少工作区。

### 2.3 显存预算（64K，q8 KV）

| 项目 | 增量 |
|---|---:|
| Stage A：两个 CPU block 移到 GPU | +324.9 MiB |
| MTP 权重（blk.64，15 个张量） | +227.9 MiB |
| MTP 单层 KV（4 KV heads × 256 × 65,536 × K/V q8_0） | +136.0 MiB（显式草稿 q8；默认 F16 为 256.0 MiB） |
| 目标模型 `embd_nextn` 缓冲（n_batch 512 × 5120 × 4B） | +10 MiB |
| MTP 图/工作区（未实测，按 100–250 MiB 估） | +100–250 MiB |
| **A+B 合计（草稿 q8）** | **约 +0.78–0.95 GiB** |
| **A+B 合计（草稿 F16）** | **约 +0.90–1.07 GiB** |

当前空闲约 386 MiB；关闭约 0.9 GiB 用户态 GPU 应用后约 1.3 GiB。A+B（q8）只剩约 0.35–0.5 GiB 余量，属于“可试但必须实测”的区间；F16 草稿余量更小。若 MTP 工作区比估算大，可能需要在 `-ngl 65`（省 162.4 MiB）与 MTP 之间取舍。
MTP 的 136 MiB（q8）KV 是按完整 65,536 上下文分配的，不能靠“短 prompt 时少分配”来省；`common/speculative.cpp` 把 `cparams.n_ctx = llama_n_ctx(ctx_tgt)`。

### 2.4 不要假设 MTP 一定提速

MTP 草稿每步要读 MTP 块（约 228 MiB）并复用目标模型的 248,320 词表输出头（约 833.6 MiB）；草稿不是免费的。是否提速取决于接受率与草稿成本。必须记录：
- `spec_decode_num_draft_tokens_total`
- `spec_decode_num_accepted_tokens_total`
- `spec_decode_num_drafts_total`
- 实际输出 token 数（不能用 synthetic acceptance）
- 首 token 延迟、decode t/s、完整耗时

若接受率低（例如每步平均接受 <1 个草稿 token），MTP 可能持平甚至更慢；此时淘汰，不补理由。

### 2.5 质量/采样影响

该版本的默认路径是“目标模型逐位置采样 + 与草稿匹配”（`common/sampling.cpp` 的 `common_sampler_sample_and_accept_n`），草稿不填分布时最终 token 仍来自目标采样；`--spec-draft-sampling probabilistic` 使用拒绝采样（源码注释明确说明保留目标分布）。因此设计上不是“用草稿替代目标”，但仍需质量回归：
- 温度 >0 时，RNG 消耗顺序改变，具体文本会与无草稿运行不同；不能拿单条输出逐字比较。
- 温度 0 时适合做确定性配对；温度 >0 时用多 seed/多次采样比较分布与正确率。
- MTP 草稿采样器内部是 top-k 10，只影响接受率，不应影响最终验证分布；仍需实测确认。
- 该版本 `common_params_speculative_draft.backend_sampling` 默认 true（`common/common.h:335`），草稿 top-k 可能在 backend 执行；这不是全局 `--backend-sampling`，`/props` 的 false 只代表主采样。记录接受率时要把这个默认值写清楚。

## 3. Stage C：独立测试项（不要和 A/B 混在一起）

### 3.1 backend sampling

```diff
+    "--backend-sampling"
```

当前 `backend_sampling=false`。248K 词表的 CPU 采样可能占每 token 数毫秒；预期 2–8% 解码提升（估算）。风险：该选项标记 experimental；部分采样器可能回退；固定 seed 不保证跨后端逐字一致。必须单独 A/B，并做质量抽查。

### 3.2 batch/ubatch

```diff
-    "-b", "512",
-    "-ub", "128",
+    "-b", "1024",
+    "-ub", "256",
```

目标是 prefill/TTFT，不是 decode 自动翻倍。当前 32K/56K prefill 约 860–924 t/s，56K TTFT 约 65 s；prefill 提升对“总答题时间”可能比 decode 提升更重要。风险：更大 ubatch 增加计算缓冲/显存，64K 下可能 OOM；一次只改一个，先 `-ub 256`，再 `-b 1024`。

### 3.3 threads

```diff
-    "-t", "6",
-    "-tb", "6",
+    "-t", "8",
+    "-tb", "8",
```

只有在仍保留 CPU 层（`-ngl 64/65`）时才有意义；完整卸载后 CPU 只做词嵌入/调度，收益预计很小。不要把它当成主要提速项。

### 3.4 cache-ram（改善重复长文的总时间，不改变 decode t/s）

```diff
-    "--cache-ram", "512",
+    "--cache-ram", "4096",
```

本机日志明确显示：56K prompt state 约 2,462.75 MiB > 512 MiB，因此被跳过，不能存入 RAM 缓存；32K 约 1.67–1.68 GiB，12K 约 1.01 GiB。提高到 4096 MiB 可容纳一个 56K/64K 状态。它不减少首次 prefill；它改善的是“同一长前缀在 slot 被其他请求挤出后再次出现”的总时间。32 GB 内存当前空闲约 10.3 GB，需监控内存压力/换页。该实验应使用完全相同的 56K prompt 连续/交错发送，记录 `cache_n`、`prompt_ms`、总墙钟。

## 4. 明确不改的项

- `-c 65536`：保持 64K 服务容量。
- 主模型、GGUF、IQ3-MIX 权重：第一阶段不变。
- `--cache-type-k q8_0`、`--cache-type-v q8_0`：第一阶段不变。
- `--reasoning on`、`--reasoning-budget 2048`：不降低思考预算；更大预算只作为独立质量实验（可按请求覆盖 `reasoning_budget_tokens`，无需改生产配置）。
- 采样默认值（temp 1.0、top_k 20、top_p 0.95、min_p 0.05、repeat_penalty 1.0）和输出长度：不作为提速手段改动。
- 不改为 32K 默认；不改为 V=q4；不降权重量化；不以 Vulkan/vLLM 替换作为第一方案；不把多请求吞吐当单请求速度。

## 5. 回滚模板

1. 备份当前配置：复制 `server-config.json` 到 `server-config.json.bak-YYYYMMDD-HHMM`，不要覆盖已有 `.bak-234549`。
2. 只编辑 `server-config.json`；不要直接改计划任务命令行。
3. 停止：`Stop-ScheduledTask -TaskName llama-server-8095`；确认 `llama-server.exe` 的 8095 进程已退出。
4. 启动：`powershell -ExecutionPolicy Bypass -File D:\llm\start-local.ps1 -Force`（该脚本会校验 `-ngl` 与配置一致）。
5. 验证：`GET /health` 为 ok；`GET /props` 的 `n_ctx=65536`；`/metrics` 的 `requests_processing=0`；`speculative.types` 与预期一致；日志无 OOM/truncated。
6. 失败回滚：停止任务，恢复备份文件，启动，重复验证。保留失败日志和基准原始记录，不删除。
7. 若只是显存不足：先关闭用户态 GPU 应用；仍不足则回退 Stage B，再回退 Stage A；不要通过缩小上下文或降低 KV 精度来“让它跑起来”。

