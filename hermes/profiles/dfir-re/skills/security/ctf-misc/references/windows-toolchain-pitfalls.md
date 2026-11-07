# Windows 工具链陷阱（中文路径环境，2026-08-26 实测验证）

适用于：Windows 11 + Git Bash(MSYS) + PowerShell 5.1 + 中文路径（D:\CTF_Misc_Tools\图像隐写\... 这类）。

## 1. .cmd 批处理：必须 GBK + CRLF
- **症状**：UTF-8 编码或 LF 行尾的 .cmd，cmd.exe 解析含多字节字符（中文路径）时吞字符/截断路径，报"不是内部或外部命令"或路径被切开（`'rityLab'`、`'CTF_MISC_Tools'` 这类残缺命令名）。
- **根因**：cmd.exe 按 ANSI/OEM 代码页（中文系统 = GBK/cp936）读批处理；LF 行尾 + 多字节字符组合会丢行尾字符。
- **方案**：用 Python 精确生成，编码 `gbk`、行尾 CRLF：
```python
with open(out, "w", encoding="gbk", newline="") as f:
    f.write('@echo off\r\nrem wrapper\r\n"目标绝对路径" %*\r\n')
```
- bash 侧同名 wrapper 保持 UTF-8 + LF（bash 无此问题）。
- 注意：bash heredoc 写 .cmd 一定中招（LF），iconv 转 GBK 不够，必须同时 CRLF。

## 2. .ps1 含中文路径：必须 UTF-8 带 BOM
- PowerShell 5.1 按 ANSI 读无 BOM 的 .ps1 → 中文字符串变乱码。
- 修复：`python -c` 读 UTF-8 写 `encoding="utf-8-sig"`，或编辑器存 BOM。

## 3. MSYS bash → PowerShell 命令行传中文参数必乱码
- bash 传 UTF-8 字节，PowerShell -Command 按控制台 ANSI(GBK) 解析 → 路径损坏（表现为"不是有效应用程序"/文件找不到）。
- **规避**：把逻辑写进 UTF-8 BOM 的 .ps1 文件，用 `powershell -NoProfile -ExecutionPolicy Bypass -File x.ps1` 执行；不要在 -Command 里内联中文路径。

## 4. MSYS 里 `cmd //c "..."` 引号会进交互模式
- 症状：打印 "Microsoft Windows [版本...]" banner 后退出，不执行命令。
- 不要用该方式测试批处理；要测就经 PowerShell 或直接执行 .cmd（bash 可直接跑 `"./x.cmd" args`）。

## 5. 部分工具经 cmd.exe 批处理层报"拒绝访问"，bash 直调正常
- 实例：binwalk/tshark/steghide 的 .cmd wrapper 经 cmd/PS 调用报 `拒绝访问`（Access denied），但同一 exe 从 bash 直接执行完全正常；qpdf/snow/dtmf2num 的 .cmd 正常。
- **根因未定**（疑似 Defender/MOTW/ADS 按路径策略；当时探测命令因等待审批被阻断，未深挖）。
- **已验证的可靠方案**：
  1. bash wrapper（`exec "D:/...exe" "$@"`）——本环境最可靠；
  2. 激活脚本直接加工具目录到 PATH（Wireshark、hashcat 安装目录这类干净目录）——原生 exe 不经批处理层；
  3. .cmd wrapper 保留但标注"部分验证"。
- 遇到"拒绝访问"不要死磕同一条路：换 bash 直调 / 加目录，如实记录未定位根因。

## 6. GUI 工具版本识别：不启动，读 PE VersionInfo
```powershell
(Get-Item -LiteralPath 'D:\path\to\app.exe').VersionInfo | Select ProductVersion, FileVersion
```
- 可批量循环；无版本资源的旧程序返回 n/a（如 MMSSTV/wbStego/SilentEye）。
- 实例：DB Browser 3.12.2 ✓；CaptfEncoder 文件名 3.1.2 但 PE 资源 3.0.0（记录差异）。

## 7. GUI 启动检查（L2）
- `powershell -Command 'Start-Process <exe>; Start-Sleep 6; $p=Get-Process -Name <名>; if($p){$p.Id; $p.MainWindowTitle; Stop-Process -Name <名> -Force}'`
- 会短暂弹窗；先确认无同名用户进程再 Stop-Process（教训：误杀过一次 cmd.exe 批处理残留，python 大进程是用户 GUI 应用——按命令行判断归属再杀）。

## 8. 路径解析要点
- bash wrapper 目标用 `D:/...` 正向斜杠可被 MSYS exec；PATH 条目必须 MSYS 风格 `/d/...`（`D:/...` 在 PATH 里不生效）。
- ps1/sh 激活脚本的 PATH 顺序：SecurityLab 工具目录 prepend、WinLibs append（避免影子 coreutils）。
