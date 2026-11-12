$ErrorActionPreference = "Stop"
$log = "D:\llm\logs\watch-start.log"
$model = "D:\llm\models\qwen3.8-27b-mix\Qwen3.8-27B-IQ3-MIX.gguf"
$expected = "3089d39401e60551a03e0858d775d6b33f966f6e6513f31f75a011cfc8f56309"

function Log($msg) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $log -Value $line -Encoding UTF8
  Write-Host $line
}

Log "watcher started; waiting for aria2 model download (PID 31392)"
$p = Get-Process -Id 31392 -ErrorAction SilentlyContinue
if ($p) { Wait-Process -Id 31392 -Timeout 7200 -ErrorAction SilentlyContinue }
Log "aria2 process ended; verifying SHA256"
if (-not (Test-Path $model)) { Log "model missing"; exit 2 }

$h = (Get-FileHash $model -Algorithm SHA256).Hash.ToLower()
if ($h -ne $expected) {
  Log "SHA256 mismatch: actual=$h expected=$expected"
  exit 3
}
Log "SHA256 OK"

if (Get-Process llama-server -ErrorAction SilentlyContinue) {
  Log "llama-server already running; skip start"
  exit 0
}

Log "starting llama-server (Vulkan, -ngl 48)"
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File D:\llm\start-27b-vulkan.ps1"
Start-Sleep -Seconds 10

for ($i = 0; $i -lt 60; $i++) {
  try {
    $r = Invoke-RestMethod "http://127.0.0.1:8095/health" -TimeoutSec 3
    Log "health OK: $($r | ConvertTo-Json -Compress)"
    exit 0
  } catch {
    Start-Sleep -Seconds 5
  }
}
Log "health did not become ready within timeout"
exit 4
