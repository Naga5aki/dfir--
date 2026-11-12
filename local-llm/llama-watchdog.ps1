# A slow/busy model must never be killed because a health probe was delayed.
$ErrorActionPreference = 'Stop'
& 'C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -B 'D:\llm\ensure_local_ready.py' *> $null
if ($LASTEXITCODE -ne 0) {
    ('{0} readiness_failed; no forced termination' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) | Add-Content -LiteralPath 'D:\llm\logs\llama-watchdog.log'
    exit 1
}
exit 0
