$ErrorActionPreference = "Stop"

$downloadUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.12.25/sherpa-onnx-1.12.25.aar"
$outDir = "c:\Users\Keith\Documents\ResKiosk\reskiosk\kiosk\libs"
$outFile = "c:\Users\Keith\Documents\ResKiosk\reskiosk\kiosk\libs\sherpa-onnx-1.12.25.aar"

if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    Write-Host "Created libs directory"
}

if (Test-Path $outFile) {
    $size = (Get-Item $outFile).Length
    Write-Host "AAR already exists ($size bytes)"
    exit 0
}

Write-Host "Downloading from: $downloadUrl"
Write-Host "Saving to: $outFile"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $outFile -MaximumRedirection 10
    $size = (Get-Item $outFile).Length
    Write-Host "Download complete! Size: $size bytes"
}
catch {
    Write-Host "ERROR: $_"
    exit 1
}
