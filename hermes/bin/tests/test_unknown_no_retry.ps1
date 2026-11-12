param([string]$Root = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$bin = Split-Path $Root -Parent
$fake = Join-Path $Root 'fake-hermes.cmd'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("unretry-" + [guid]::NewGuid().ToString('N'))
$notes = Join-Path $tmp 'notes'
New-Item -ItemType Directory -Force -Path $notes | Out-Null
Set-Content -LiteralPath (Join-Path $notes 'q.txt') -Value '1|写出苹果手机的序列号' -Encoding UTF8

& powershell -NoProfile -File (Join-Path $bin 'dfir-solve.ps1') -Questions 1 -QuestionsFile (Join-Path $notes 'q.txt') `
    -CaseRoot $tmp -Domain mobile -HermesCommand $fake -SkipMount -SkipMyos -SkipEvidencePack -SkipEvalGold *> $null

$log = Get-Content (Join-Path $notes '_solve.log') -Raw -Encoding UTF8
$line = [regex]::Match($log, '(?m)^Q1 \|.*UNKNOWN.*$').Value
Write-Host $line
if ($line -match 'attempt=1') { Write-Host 'PASS'; exit 0 }
Write-Host 'FAIL: UNKNOWN retried'
exit 1
