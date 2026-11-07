param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dfir','dfir-myos','dfir-re','dfir-mem','dfir-pcap','dfir-max')]
    [string]$Profile,
    [switch]$Probe,
    [string]$HermesRoot = (Join-Path $env:LOCALAPPDATA 'hermes'),
    [string]$ProfilesRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'profiles')
)
$ErrorActionPreference = 'Stop'
$factsCandidates = @(Get-ChildItem -LiteralPath (Join-Path $HermesRoot 'installs') -Directory | ForEach-Object {
    $candidate = Join-Path $_.FullName 'facts.json'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $candidate }
})
if ($factsCandidates.Count -ne 1) { throw 'Hermes runtime is ambiguous; specify the intended HermesRoot. No installation attempted' }
$factsPath = $factsCandidates[0]
$facts = Get-Content -Raw -LiteralPath $factsPath | ConvertFrom-Json
$pythonPath = Join-Path $facts.packages.venv.environment 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw 'Existing Hermes Python not found; no installation attempted' }
$checkerArgs = @('-X','utf8','-B',(Join-Path $PSScriptRoot 'dfir_preflight.py'),'--profile',$Profile,'--profiles-root',$ProfilesRoot)
if ($Probe) { $checkerArgs += '--probe' }
& $pythonPath @checkerArgs
exit $LASTEXITCODE
