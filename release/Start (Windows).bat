@echo off
rem Double-click to start EPM2Mod on Windows. If Windows protects your PC: More info, then Run anyway.
rem A module path inherited from PowerShell 7 breaks Windows PowerShell's own commands: start it with its default.
set "PSModulePath="
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "EPM2_EXIT=%ERRORLEVEL%"
rem keep the window open to show an error; CI (which sets CI) has no one to press a key
if not "%EPM2_EXIT%"=="0" if not defined CI pause
exit /b %EPM2_EXIT%
