@echo off
chcp 65001 >nul 2>&1
title MusicRate 后端服务

REM 自动定位到脚本所在目录（即项目根目录），无论盘符是什么
cd /d "%~dp0"

echo ============================
echo   MusicRate 后端启动
echo ============================
echo.

REM 使用项目内嵌的便携 Python 启动
python\python.exe backend\run.py

pause
