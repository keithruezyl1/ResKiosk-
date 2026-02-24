@echo off
echo Downloading sherpa-onnx AAR from GitHub releases...
echo This may take a minute (~40MB file)...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0download_aar.ps1"
echo.
if exist "%~dp0libs\sherpa-onnx-1.12.25.aar" (
    echo SUCCESS: AAR file downloaded.
) else (
    echo FAILED: AAR file not found after download.
)
pause
