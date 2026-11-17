@echo off
rem Double-click to start EPM2Mod on Windows. If Windows protects your PC: More info, then Run anyway.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
rem keep the window open to show an error; CI (which sets CI) has no one to press a key
if errorlevel 1 if not defined CI pause
