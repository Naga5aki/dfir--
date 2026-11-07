# 桌面自动化兜底通道（cua-driver CLI，最后手段）

场景：用户要求"执行"一个只能从桌面 UI 发出的动作（典型：会话内 `/reload-mcp`），而**先行的证伪步骤**（运行时自动机制 / 配置变更 / CLI 与进程操作）都不适用时，才轮到本通道。

## 已验证可用的只读链（本机实测）

- 二进制：`~/.cua-driver/packages/releases/<ver>-x86_64-pc-windows-msvc/cua-driver.exe`（多版本并存，取最新；另有 `cua-driver-uia.exe`）。
- `cua-driver status` — 守护状态（socket / pid / permission mode）。**守护是否在跑与 Hermes `computer-use status` 的 "installed" 标记相互独立**——以 `cua-driver status` 实测为准。
- `cua-driver list-tools` — 全工具表（list_apps / list_windows / get_window_state / click / type_text / press_key / set_value / debug_window_info …）。
- `cua-driver describe <tool>` — 取参数 schema（含快照与 element 索引使用纪律；Electron 网页输入框注意：UIA `set_value` 可能被忽略，文本输入优先 `type_text`）。
- `cua-driver call <tool> '<json>'` — 调用。bash 下**单引号包 JSON 作位置参数**（`call debug_window_info '{"pid":27972}'` 实测可用；无参工具直接 `call list_apps`）。PowerShell 5.1 会剥引号 → 用 stdin：`'{"pid":123,"window_id":456}' | cua-driver call get_window_state`。

## 目标发现套路

1. `call list_apps` — 应用清单（name / pid / launch_path；另有 processes 段）。
2. `call list_windows` — window_id + 屏幕坐标 + minimized 标志（分段结构：`_legacy_windows` 与增强段）。
3. `call debug_window_info '{"pid":N}'` — 单窗口深挖（类名 / focused_element，含只读标志）。
4. 输入动作（click / type_text / press_key）前先 `get_window_state` 取元素索引；索引随快照失效，每次动作前重取。

## 纪律（比命令更重要）

- **能改配置、能跑 CLI、能等自动机制解决的，绝不碰 UI。** UI 驱动是最后一档；最小化 / 后台窗口上的输入动作不可靠——先只读探明结构，再评估是否值得打扰用户。
- 对用户窗口做任何输入前，先确认"没有更安静的路"（本例：查到"回合间自动刷新"机制后，UI 通道整体不再需要）。
- Hermes 会话工具面未必挂载 `computer_use` 工具集，但这不妨碍 CLI 直用（两者独立）。

## 未验证边界（用前先只读探路）

- 本环境仅验证到"发现 / 描述 / 调用只读工具"（status / list-tools / describe / call 只读类）。
- 对具体应用窗口做输入动作（click / type_text / press_key）的完整链路**未在本环境实测**；若必须使用，从只读快照起步、小步验证、随时可停。
