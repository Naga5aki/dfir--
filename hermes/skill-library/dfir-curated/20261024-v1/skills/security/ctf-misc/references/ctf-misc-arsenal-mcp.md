# CTF Misc Arsenal MCP（Hermes 接入与调用手册）

本机综合工具「CTF Misc Arsenal」（`D:\CTF_Misc_Tools\图像隐写\CTF-Misc-Arsenal.exe`，v1.3.1）已通过
HTTP MCP 接入 Hermes：`http://127.0.0.1:41215/mcp` + Bearer Token（`.env` 的
`MCP_CTF_MISC_ARSENAL_API_KEY`；token 原始副本在程序 `config/config.json` 的 `mcp.token`）。
完整注册记录与 54 工具清单：`D:\Hermes\SecurityLab\ctf-misc-arsenal-mcp-setup.md`。
**调用前无需手动启动程序**——已配置 pre_tool_call 钩子自动拉起应用并等待就绪；若因桌面端启动时程序未运行导致**整个会话缺少该工具集**，先执行一次钩子脚本恢复（详见「前置与故障排查」的恢复配方）。

## 何时用（题型 → 首选工具）

| 题型 | 首选 MCP 工具（`mcp__ctf_misc_arsenal__` 前缀省略） |
|---|---|
| 图像隐写（位平面/LSB/通道） | `stegsolve`（mode=analyse 出位平面产物）、`zsteg`、`stegsolve_combiner` |
| PNG 结构 / IDAT 藏数 | `png_idat_analysis`（inspect/extract、可 zlib_inflate、块表达式） |
| 宽/高被改（CRC 不符、显示不全） | `image_width_bruteforce`、`image_height_fixer` |
| 周期变换类（Arnold/ZigZag/Hilbert/Peano） | 同名工具，`times`/`a`/`b` 支持范围语法如 `1-8`、`1,3,5` |
| 加密隐写工具（要口令） | `steghide`/`stegpy`/`f5`/`outguess`/`jphs`/`jsteg`/`cloacked_pixel`（password/brute_force + dictionary） |
| 立体图 / 光栅动画 | `stereogram_solver`、`barrier_grid_animation` |
| 动图 | `animated_image_analysis`（extract_frames / timing_analysis） |
| 音频：DTMF / Morse / SSTV / Weatherfax | `dtmf_decoder`、`morse_decoder`、`sstv_decoder`、`weatherfax_decoder` |
| MP3 隐写 | `mp3stego`、`mp3_frame_bits_analysis` |
| 音频隐写（WAV/FLAC/BMP/JPEG 组合） | `silenteye`、`deepsound`、`s_tools_v4`、`stegolsb` |
| 文本：零宽 / base 填充位 / SNOW | `zero_width_steganography`、`base_padding_steganography`、`snow` |
| 压缩包 | `zip_plaintext_attack`（明文攻击）、`zip_sparse_plaintext_attack`（稀疏明文）、`zip_pseudo_encryption_repair`（伪加密） |
| 哈希识别 → 爆破 | 先 `hash_type_identifier`（返回 hashcat 模式号 + john 格式名），再 `hashcat`/`john`；字典用 `dictionary_builder`（mask/slice/merge/social） |
| 碰撞 | `fastcoll`（MD5 前缀碰撞）、`sha1collider`（PDF SHA-1 碰撞） |
| 通用雕刻/字符串/元数据/类型 | `binwalk`（carve/matryoshka）、`foremost`、`strings`（多编码/regex 预设）、`exiftool`、`magika` |
| 拼图/重排（遗传算法求解） | `gaps`（generations/population） |
| aCropalypse 截图恢复 | `acropalypse_restoration`（detect/restore/brute_force + 机型预设） |
| 条码 / 等距像素 | `common_barcode_reader`、`equidistant_pixel_extractor` |

## 调用约定（重要）

1. 工具名：`mcp__ctf_misc_arsenal__<工具名>`；`input`/`input2` 均为**应用所在主机的绝对路径**（本机即当前机器）。
2. 读结果：`content` 往往只是摘要甚至是空串；**数据主体在 `structured_content`**：
   `status`(completed/partial/no_result/failed/cancelled)、`message`、`summary`(finding_count/artifact_count)、
   `preview.data`（解析记录/识别结果）、`preview.findings`（如 hash 候选表）、`truncated`+`continuation`。
3. 产物（artifacts）：每项含 `name`/`media_type`/`size`/`digest`(blake3)/`uri`；用
   `mcp__ctf_misc_arsenal__read_resource` 读 `arsenal-result://result/<id>/artifact/<aid>/<chunk>`（二进制以 base64 blob 返回）；
   清单用 `.../manifest`；大数据的续读取 `.../data/<chunk>`。列表资源为空，地址一律取自工具返回值的 `uri` 字段。
4. 枚举参数**显式传值**：实测 `stegsolve` 不传 `mode` 直接报 `Invalid JSON: missing field 'mode'`；
   建议所有 enum/关键参数都写明（如 `mode="analyse"`、`bit_planes`、`channel_order`）。
5. 长任务（hashcat/john/binwalk matryoshka/宽度爆破/brute_force）耗时可达分钟级，调用前心里有超时预算；
   需要时把范围参数写小做定点测试。
6. **每次 `tool_call` 只装 1 个条目**（本地/MCP 工具不支持多条目批量，运行时会直接拒绝并提示拆开）；需要连发多个时用多个 `tool_call`（同一消息可并行发出）。多个同名调用并行时 `same_tool_failure_warning` 计数可能误报——逐条结果以实际 `status` 为准（completed 即成功），勿因计数误报废弃有效调用。
7. **位敏感文本参数的转写**（`snow`/`zero_width_steganography` 等按位还原的工具）：用 python `json.dumps(text, ensure_ascii=False)` 生成转义串存档，写入 `tool_call` 参数时把转义降一层（显示为 `\\t`/`\\r\\n` 的写成 `\t`/`\r\n`，由参数 JSON 层还原为真实 TAB/CRLF）；中文等非 ASCII 字符原样写入即可。这类工具位敏感——**解码成功即证明转写逐字节保真**；解码失败时先怀疑转写（与源文件 sha256 复核）再怀疑方法。

## 前置与故障排查（自动拉起已就位）

- **无需手动先启动程序**：已配置 Hermes shell hook（`pre_tool_call`，matcher `mcp__ctf_misc_arsenal__.*`），
  调用任何本服务器工具前会自动拉起 `CTF-Misc-Arsenal.exe` 并以 initialize 探测等待就绪（约 8~12s）再执行。
  钩子脚本 `~/AppData/Local/hermes/agent-hooks/ctf-arsenal-ensure.py`；日志 `~/AppData/Local/hermes/logs/ctf-arsenal-ensure.log`。
  拉起后**自动最小化**（后台运行，不弹窗打扰；`CTF_ARSENAL_WINDOW=hidden/show` 可改），最小化状态下工具调用正常。
- **⚠️ 已知缺口（2026-09-27 实测）：桌面端启动时程序未在运行** → MCP 发现失败 → **整会话缺少 `mcp__ctf_misc_arsenal__*` 工具集**（tool_search 无此来源）；此时钩子无从触发——它只对"工具已在会话中"的调用生效。
- **恢复配方（标准动作；"要调用但程序未启动时：自行启动、后台运行、继续调用"，不得因未启动而放弃）**：
  1. 执行一次钩子脚本（分离进程拉起程序 + 等就绪 + 实例自动最小化，后台运行不弹窗）：
     `python C:/Users/TWK/AppData/Local/hermes/agent-hooks/ctf-arsenal-ensure.py`
  2. 等待客户端自动重连：**异步、可能需数分钟**（实测 30 秒后仍未出现，其后数分钟内恢复；其间可继续其他准备工作）——以 `tool_search` 来源列表重新出现 `ctf-misc-arsenal`（56 工具），或 `tool_describe` 能试载任一 `mcp__ctf_misc_arsenal__*` 名为准；久未恢复再用 `/reload-mcp` 或重启桌面端强制刷新；
  3. 自检 `hermes mcp test ctf-misc-arsenal`（应 ✓ Connected + 54 工具）；恢复后先做一次无害调用终验（如 `hash_type_identifier` → `status=completed`）再继续调用。
- **⚠️ 钩子 fail-closed 阻塞全部工具（2026-10-10 实测）**：端点掉线时触发钩子会 fail-closed，**所有工具调用**（不止 arsenal）在约 60~90 秒内被 `pre_tool_call plugin callback timed out or is still running` 阻塞，修复后自行恢复；若实例处于“进程在、端点起不来”的坏状态（ensure 日志出现 `giving up — emitting block directive`），先杀光全部实例再跑脚本（`taskkill /F /IM CTF-Misc-Arsenal.exe` → 跑钩子脚本 → 日志见 `endpoint ready`），再 `hermes mcp test` 验证（应 ✓ 54 工具）。**活动会话中工具集不会因端点恢复而自动重新注册**（实测等待 ~20 分钟 tool_search 仍无来源）——用 `/reload-mcp` 或重启桌面端刷新。
- 若只是"工具在、连接断"（transport is down）：无需脚本，等 5~10 秒重试即可。
- **调用报错的正确处理**：
  - `transport is down / reconnect requested` → Hermes 客户端在后台重建连接：**等 5~10 秒重试一次**即通（别连发）。
  - `unreachable after N consecutive failures`（熔断）→ 等 30~60 秒再试。
  - 钩子超时返回中文 block 指令 → 按提示手动启动程序后重试。
- 自检：`hermes mcp test ctf-misc-arsenal`（应 ✓ Connected + 54 工具）、`hermes hooks doctor`。
- 界面「轮换」Token 后：同步更新 `~/AppData/Local/hermes/.env` 的 `MCP_CTF_MISC_ARSENAL_API_KEY`
  （或直接读 `D:\CTF_Misc_Tools\图像隐写\config\config.json` 的 `mcp.token`）。token 含小写 `l`，勿按 `1` 抄录。
- 本后端进程新增工具后需 `/reload-mcp`（会失效一次提示缓存，属正常）；重启桌面端亦自动发现。

## 验证快照（2026-09-27）

54 工具全枚举；`hash_type_identifier`/`strings`/`magika`/`stegsolve`/`zero_width_steganography`
在合成良性样本上闭环通过（stegsolve 39 个位平面产物经 read_resource 成功取回）。
`snow` 在真实空白隐写文本上提取通过，并与本地 SNOW.EXE **全路径行为等价**（正确解码/空载荷/两种模式错配路径逐字节一致——可互为对照实现）；恢复配方演练：程序未运行 → 脚本拉起 → 会话自动重连 → `hash_type_identifier`/`strings`/`magika`/`snow` 直调全部 completed（2026-09-27 晚）。
