# 本地模型服务快照（2026-11-12）

这是 `D:\llm` 中配置与启动脚本的快照，随主仓库提交，用于回退。运行中的服务仍以 `D:\llm` 为准，本目录不自动同步。

## 服务

- 引擎：llama.cpp `b11714`（commit `c0fd78626`），CUDA 构建，监听 `127.0.0.1:8095`
- 模型：`D:\llm\models\qwen3.8-27b-mix\Qwen3.8-27B-IQ3-MIX.gguf`（12,586,448,320 字节）
- API key：`D:\llm\secrets\llama.key`（**不在本仓库**，`server-config.json` 只引用路径）
- 启动：计划任务 `llama-server-8095` → `run_server.py` → 读取 `server-config.json` 拉起 `llama-server.exe`
- 就绪检查：`ensure_local_ready.py`（Hermes 的 `pre_llm_call` 钩子也调用它）

## 当前参数（与 server-config.json 一致）

`-c 65536 -np 1 -ngl 64 -b 512 -ub 128 -t 8 -tb 8 --flash-attn on`，KV 均为 `q8_0`，`--cache-ram 512`，`--cache-reuse 256`，`--reasoning-format deepseek --reasoning-budget 2048`，原生 MTP：`--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 --spec-draft-n-ubatch 128`。

2026-11-07 起线上窗口为 64K。16GB 显卡下 35K 以上长会话 decode 会明显下降；单题提示应控制在 3 万 token 内，详见 `reports/本地模型性能与质量评估-2026-10-30.md`。

## 不在此快照内

- 模型权重（12.5GB）、llama.cpp 二进制与 DLL、日志
- `secrets/`（API key）
- `server-config.json.bak-*` 历史备份（仍保留在 `D:\llm`）

## 回退方法

1. 安装或找回 llama.cpp `b11714` / `c0fd78626` 的 CUDA 构建到 `D:\llm\llama.cpp\`。
2. 把本目录的 `server-config.json` 和各脚本复制回 `D:\llm\`（同名覆盖）。
3. 重新放好 `D:\llm\secrets\llama.key` 与模型文件。
4. 运行 `powershell -File D:\llm\start-local.ps1` 重启计划任务；用 `curl -s http://127.0.0.1:8095/health` 确认。

`start-27b-vulkan*.ps1` 是更早的 Vulkan 变体，保留作参考，当前线上不用。
