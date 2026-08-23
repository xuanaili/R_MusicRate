@echo off
rem ==== MusicRate one-click launcher (double-click me) ====
chcp 65001 >nul
title MusicRate One-Click Start
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_musicrate.ps1"
if errorlevel 1 (
    echo.
    echo Start failed. Press any key to close this window...
    pause >nul
)