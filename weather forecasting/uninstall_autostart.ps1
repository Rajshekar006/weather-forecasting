$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Weather Forecast.lnk"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$desktopShortcut = Join-Path $desktopPath "Weather Forecast.url"

if (Test-Path $shortcutPath) {
  Remove-Item $shortcutPath -Force
  Write-Host "Removed startup entry."
} else {
  Write-Host "No startup entry found."
}

if (Test-Path $desktopShortcut) {
  Remove-Item $desktopShortcut -Force
  Write-Host "Removed desktop shortcut."
}

Write-Host ""
Write-Host "Autostart removed. The app will no longer start on login."
Write-Host "You can still run start_weather.bat manually."
