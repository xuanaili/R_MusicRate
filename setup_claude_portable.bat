@echo off
chcp 65001 >nul 2>&1
title MusicRate - Claude Code 便携配置

REM 自动定位到脚本所在目录
cd /d "%~dp0"

echo ============================
echo   Claude Code 便携配置
echo ============================
echo.

REM ===== 1. 计算当前项目路径的 Claude 项目目录名 =====
REM Claude Code 将路径中的 : 替换为 --，\ 替换为 --
REM 例如 U:\MusicRate → U--MusicRate
REM 提取盘符和目录名
for %%I in ("%~dp0..") do set "PROJECT_DIR=%%~fI"
set "PROJECT_DIR=%PROJECT_DIR: =%"

REM 从完整路径生成 Claude 项目目录名
REM 去掉冒号，将反斜杠替换为 --
set "CLAUDE_DIR_NAME=%PROJECT_DIR::=%"
set "CLAUDE_DIR_NAME=%CLAUDE_DIR_NAME:\=--%"

echo 项目路径: %PROJECT_DIR%
echo Claude目录名: %CLAUDE_DIR_NAME%
echo.

REM ===== 2. 创建记忆目录的 Junction =====
set "CLAUDE_PROJECT_DIR=%USERPROFILE%\.claude\projects\%CLAUDE_DIR_NAME%"
set "MEMORY_TARGET=%~dp0.claude\memory"

if not exist "%MEMORY_TARGET%" mkdir "%MEMORY_TARGET%"

if exist "%CLAUDE_PROJECT_DIR%\memory" (
    echo [记忆] 已存在，跳过
) else (
    if not exist "%CLAUDE_PROJECT_DIR%" mkdir "%CLAUDE_PROJECT_DIR%"
    mklink /J "%CLAUDE_PROJECT_DIR%\memory" "%MEMORY_TARGET%"
    echo [记忆] Junction 创建成功 ✓
)

REM ===== 3. 复制全局设置（如果不存在） =====
set "GLOBAL_SETTINGS=%USERPROFILE%\.claude\settings.json"
set "PORTABLE_SETTINGS=%~dp0.claude\settings.json"

if exist "%PORTABLE_SETTINGS%" (
    if not exist "%GLOBAL_SETTINGS%" (
        if not exist "%USERPROFILE%\.claude" mkdir "%USERPROFILE%\.claude"
        copy "%PORTABLE_SETTINGS%" "%GLOBAL_SETTINGS%" >nul
        echo [设置] 全局设置已复制 ✓
    ) else (
        echo [设置] 全局设置已存在，跳过
    )
) else (
    echo [设置] 未找到便携设置文件，跳过
)

echo.
echo ============================
echo   配置完成！
echo ============================
echo.
echo 现在可以运行 claude 启动项目了
pause
