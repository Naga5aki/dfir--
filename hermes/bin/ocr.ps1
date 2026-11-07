param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$Lang = 'zh-Hans-CN',
    [string]$Out
)
# 图片 OCR（Windows 自带 Windows.Media.Ocr，离线、无需安装 tesseract）
# 单文件：ocr.ps1 -Path x.jpg
# 整目录：ocr.ps1 -Path <目录> -Out notes\ocr-Q3.txt
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Lang))
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if (-not $engine) { throw "当前系统没有可用的 OCR 语言包（需要 zh-Hans-CN 或 en-US）" }

$files = if (Test-Path $Path -PathType Container) {
    Get-ChildItem $Path -Recurse -File | Where-Object { $_.Extension -in '.jpg', '.jpeg', '.png', '.bmp' }
} else { Get-Item $Path }

$sb = [System.Text.StringBuilder]::new()
foreach ($f in $files) {
    [void]$sb.AppendLine("===== $($f.Name) =====")
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $result.Lines | ForEach-Object { [void]$sb.AppendLine($_.Text) }
        $stream.Dispose()
    } catch {
        [void]$sb.AppendLine("[OCR_FAIL] $($_.Exception.Message)")
    }
}
if ($Out) { $sb.ToString() | Out-File -FilePath $Out -Encoding utf8 } else { $sb.ToString() }
