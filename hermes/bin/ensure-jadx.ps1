# 确保 jadx-gui（含 AI MCP 插件）在 8650 就绪，并把目标 APK 作为项目打开。
# 为什么：dfir-max 的 jadx MCP 只连 GUI 插件；GUI 未运行时报 "Cannot connect to JADX plugin at :8650"，
#        模型常在这一点上耗掉整轮预算（Q15 实测 2 次尝试后仍 UNKNOWN）。
# 用法：
#   powershell -File ensure-jadx.ps1                       # 只检查/拉起 GUI（不打开项目）
#   powershell -File ensure-jadx.ps1 -Apk <apk路径>         # 拉起 GUI 并打开项目（检材里的 APK 会先复制到工作区）

param(
    [string]$Apk = '',
    [int]$Wait = 90
)

$ErrorActionPreference = 'Continue'
$exe = 'D:\CTF_Misc_Tools\reverse\jadx\jadx-gui-1.5.6.exe'
$scratch = 'D:\ForensicsAgent\hermes\profiles\dfir-max\cache\scratch\jadx'

function Test-Port {
    return (Test-NetConnection -ComputerName 127.0.0.1 -Port 8650 -InformationLevel Quiet -WarningAction SilentlyContinue)
}

if (-not (Test-Path $exe)) {
    "jadx-gui 不存在：$exe" | Write-Error
    exit 2
}

$target = $null
if ($Apk) {
    if (-not (Test-Path $Apk)) { "APK 不存在：$Apk" | Write-Error; exit 3 }
    New-Item -ItemType Directory -Force -Path $scratch | Out-Null
    $target = Join-Path $scratch (Split-Path $Apk -Leaf)
    if (-not (Test-Path $target)) { Copy-Item $Apk $target -Force }
}

if (Test-Port) {
    if ($target) { Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "`"$exe`" `"$target`"" } | Out-Null }
    "JADX_MCP_OK already-running"
    exit 0
}

# 用 WMI 拉起：普通 Start-Process 的 GUI 子进程会随终端会话结束被回收（实测 30s 内消失），WMI 由 WmiPrvSE 托管可常驻
$cmd = if ($target) { "`"$exe`" `"$target`"" } else { "`"$exe`"" }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
if ($r.ReturnValue -ne 0) { "WMI 启动失败 return=$($r.ReturnValue)" | Write-Error; exit 5 }

$deadline = (Get-Date).AddSeconds($Wait)
while ((Get-Date) -lt $deadline) {
    if (Test-Port) { "JADX_MCP_OK started"; exit 0 }
    Start-Sleep -Seconds 3
}
"JADX_MCP_FAIL 端口 8650 在 $Wait 秒内未就绪；请检查 jadx-gui 是否打开了项目或插件是否启用" | Write-Error
exit 4
