$src = "e:\sam_runtime_bundle_20260329_100640.zip"
$partDir = "e:\sam_runtime_bundle_20260329_100640_parts"
$chunkSize = 29MB

if (!(Test-Path $src)) {
    throw "Source zip not found: $src"
}

if (Test-Path $partDir) {
    Remove-Item $partDir -Recurse -Force
}

New-Item -ItemType Directory -Path $partDir | Out-Null

$fs = [System.IO.File]::OpenRead($src)
try {
    $buffer = New-Object byte[] $chunkSize
    $index = 1
    while (($read = $fs.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $partPath = Join-Path $partDir ([System.IO.Path]::GetFileName($src) + ".part" + $index.ToString("000"))
        $out = [System.IO.File]::Create($partPath)
        try {
            $out.Write($buffer, 0, $read)
        } finally {
            $out.Dispose()
        }
        $index++
    }
} finally {
    $fs.Dispose()
}

$rebuild = @'
$parts = Get-ChildItem "e:\sam_runtime_bundle_20260329_100640_parts\sam_runtime_bundle_20260329_100640.zip.part*" | Sort-Object Name
$dest = "e:\sam_runtime_bundle_20260329_100640_rebuilt.zip"
$out = [System.IO.File]::Create($dest)
try {
    foreach ($part in $parts) {
        $bytes = [System.IO.File]::ReadAllBytes($part.FullName)
        $out.Write($bytes, 0, $bytes.Length)
    }
} finally {
    $out.Dispose()
}
Write-Output "REBUILT=$dest"
'@

Set-Content -Path (Join-Path $partDir "rebuild_zip.ps1") -Value $rebuild -Encoding UTF8

Get-ChildItem $partDir -File | Select-Object Name, @{Name = "SizeMB"; Expression = { [math]::Round($_.Length / 1MB, 2) } }
