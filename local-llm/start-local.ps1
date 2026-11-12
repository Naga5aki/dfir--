param([int]$Ngl=64,[switch]$Force)
$ErrorActionPreference='Stop'
$taskName='llama-server-8095'
# Refuse an unreadable task instead of killing every local model as a fallback.
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$config=Get-Content -LiteralPath 'D:\llm\server-config.json' -Raw | ConvertFrom-Json
$layerIndex=[Array]::IndexOf($config.command,'-ngl')
if($PSBoundParameters.ContainsKey('Ngl') -and "$Ngl" -ne $config.command[$layerIndex+1]){
    throw 'Ngl differs from server-config.json. Update that file explicitly before a restart.'
}
if($Force){
    Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" | Where-Object {
        $_.ExecutablePath -in @('D:\llm\llama.cpp\llama-server.exe','D:\llm\llama.cpp-vulkan\llama-server.exe') -and $_.CommandLine -match '--port\s+8095(?:\s|$)'
    } | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop}
}
& 'C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -B 'D:\llm\ensure_local_ready.py'
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'llama-server ready at http://127.0.0.1:8095/v1 (windowless scheduled task)'
exit 0
