# dfir 系列统一包装：挂载 -> 预算基线 -> Hermes -> 收口检查 -> 卸载
# 关键点：清理放在 finally 中，Ctrl+C 中断 pipeline 时仍会执行。
param(
    [Parameter(Mandatory = $true)][string]$Profile,
    [switch]$Mount,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)

$ErrorActionPreference = 'Continue'
$python = 'C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe'
$bin = 'D:\ForensicsAgent\hermes\bin'

# 定位案例目录：D:\forensics 是指向外置盘的联接，盘符变动时回退到各盘探测
$caseRoot = 'D:\forensics\cases'
if (-not (Test-Path $caseRoot)) {
    $caseRoot = Get-PSDrive -PSProvider FileSystem |
        ForEach-Object { Join-Path $_.Root 'Forensics\cases' } |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1
}
if (-not $caseRoot) {
    Write-Host 'ERROR: 找不到取证案例目录 D:\forensics\cases（外置盘未挂载或盘符已变），请检查后重试。' -ForegroundColor Red
    exit 1
}
Set-Location $caseRoot

try {
    if ($Mount) {
        & $python "$bin\myos_mount.py" mount *> $null
        # 挂载后刷新数据源地图（增量：root 未变则直接复用），模型不必再枚举包与库
        & $python "$bin\myos_appmap.py" *> $null
    }
    & $python "$bin\budget_guard.py" begin --profile $Profile *> $null

    & hermes -p $Profile @Rest
}
finally {
    & $python "$bin\budget_guard.py" end --profile $Profile *> $null
    if ($Mount) {
        & $python "$bin\myos_mount.py" unmount *> $null
    }
}
