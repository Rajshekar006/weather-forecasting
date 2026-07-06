$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath = Join-Path $projectDir "start_weather_hidden.vbs"
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Weather Forecast.lnk"
$urlPath = Join-Path $projectDir "Weather Forecast.url"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$desktopShortcut = Join-Path $desktopPath "Weather Forecast.url"

if (-not (Test-Path $vbsPath)) {
  throw "Missing file: $vbsPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $vbsPath
$shortcut.WorkingDirectory = $projectDir
$shortcut.WindowStyle = 7
$shortcut.Description = "Start Weather Forecast on http://127.0.0.1:5050"
$shortcut.Save()

@"
[InternetShortcut]
URL=http://127.0.0.1:5050
IconIndex=0
"@ | Set-Content -Path $urlPath -Encoding ASCII

Copy-Item -Path $urlPath -Destination $desktopShortcut -Force

Write-Host ""
Write-Host "Weather Forecast is set up as a permanent local app."
Write-Host ""
Write-Host "Permanent URL: http://127.0.0.1:5050"
Write-Host ""
Write-Host "What was installed:"
Write-Host "  - Windows Startup entry (starts automatically when you log in)"
Write-Host "  - Desktop shortcut: Weather Forecast.url"
Write-Host ""
Write-Host "Starting the server now..."
Start-Process -FilePath $vbsPath
Write-Host "Done."
