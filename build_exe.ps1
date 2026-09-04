# build_exe.ps1 - Build standalone exe with yt-dlp + ffmpeg bundled
$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot
Set-Location $ROOT

Write-Host "== Checking requirements ==" -ForegroundColor Cyan
try { & python -m pip install -q --upgrade yt-dlp pyinstaller --disable-pip-version-check 2>$null } catch {}
$FF = "C:\yt\bin\ffmpeg.exe"
if (-not (Test-Path $FF)) { $FF = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source }
$FFP = "C:\yt\bin\ffprobe.exe"
$YT = "C:\yt\yt-dlp.exe"
if (-not (Test-Path $YT)) { $YT = (Get-Command yt-dlp -ErrorAction SilentlyContinue).Source }
Write-Host "FFmpeg: $FF" -ForegroundColor Green
Write-Host "yt-dlp: $YT" -ForegroundColor Green
$ICON = Join-Path $ROOT "app.ico"
if (-not (Test-Path $ICON)) { $ICON = "NONE" } else { $ICON = "`"$ICON`"" }
Write-Host "Icon: $ICON" -ForegroundColor Green

Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item -Force yt-dlp-GUI.spec, yt-dlp-GUI-Portable.spec -ErrorAction SilentlyContinue

Write-Host "`n== Building OneDir (recommended, supports yt-dlp -U) ==" -ForegroundColor Cyan
$ICON_DATA = ""
if (Test-Path (Join-Path $ROOT "app.ico")) { $ICON_DATA = " --add-data `"$ROOT\app.ico;.`"" }
if (Test-Path (Join-Path $ROOT "icon.png")) { $ICON_DATA += " --add-data `"$ROOT\icon.png;.`"" }
if (Test-Path (Join-Path $ROOT "yt-dlp-logo.png")) { $ICON_DATA += " --add-data `"$ROOT\yt-dlp-logo.png;.`"" }
$cmd = "pyinstaller --noconfirm --onedir --windowed --name yt-dlp-GUI --icon $ICON --hidden-import yt_dlp --collect-all yt_dlp --hidden-import yt_dlp.extractor"
if (Test-Path $FF)  { $cmd += " --add-binary `"$FF;.`"" }
if (Test-Path $FFP) { $cmd += " --add-binary `"$FFP;.`"" }
if (Test-Path $YT)  { $cmd += " --add-binary `"$YT;.`"" }
$cmd += $ICON_DATA
$cmd += " app.py"
Write-Host $cmd -ForegroundColor DarkGray
Invoke-Expression $cmd

Write-Host "`n== Building OneFile (portable single file) ==" -ForegroundColor Cyan
$cmd2 = "pyinstaller --noconfirm --onefile --windowed --name yt-dlp-GUI-Portable --icon $ICON --hidden-import yt_dlp --collect-all yt_dlp"
if (Test-Path $FF)  { $cmd2 += " --add-binary `"$FF;.`"" }
if (Test-Path $FFP) { $cmd2 += " --add-binary `"$FFP;.`"" }
if (Test-Path $YT)  { $cmd2 += " --add-binary `"$YT;.`"" }
$cmd2 += $ICON_DATA
$cmd2 += " app.py"
Write-Host $cmd2 -ForegroundColor DarkGray
Invoke-Expression $cmd2

Write-Host "`n== Done ==" -ForegroundColor Green
Get-ChildItem dist | Format-Table Name, Length, LastWriteTime -AutoSize
Write-Host "`nOneDir: dist\yt-dlp-GUI\yt-dlp-GUI.exe (recommended)"
Write-Host "OneFile: dist\yt-dlp-GUI-Portable.exe (single file)"
