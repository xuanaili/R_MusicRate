# MusicRate 一键启动脚本
# 功能：
#   1. 启动后端 Flask（:5000，portable python，自动拉起 MySQL80 服务）
#   2. 启动前端 vue-cli dev server（:8080）
#   3. 轮询等待两个服务就绪，自动打开浏览器进入前端页面
#   4. 若桌面尚无快捷方式，自动创建一个带 musicrate.ico 图标的 .lnk
# 用法：双击 start_musicrate.bat（或直接 powershell -ExecutionPolicy Bypass -File start_musicrate.ps1）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$BackendPort = 5000
$FrontendPort = 8080
$FrontendUrl = "http://localhost:$FrontendPort"

# ---------- 工具函数 ----------
function Test-PortOpen([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(300)
        if (-not $ok) { return $false }
        $client.EndConnect($iar)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Write-Step([string]$msg) {
    Write-Host "[MusicRate] $msg" -ForegroundColor Cyan
}

# ---------- 桌面快捷方式（不存在才创建） ----------
function Install-DesktopShortcut {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk = Join-Path $desktop 'MusicRate 启动.lnk'
    if (Test-Path $lnk) { return }
    try {
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($lnk)
        $sc.TargetPath = Join-Path $root 'start_musicrate.bat'
        $sc.WorkingDirectory = $root
        $sc.IconLocation = Join-Path $root 'launcher\musicrate.ico'
        $sc.Description = '一键启动 MusicRate 前后端并自动打开浏览器'
        $sc.Save()
        Write-Step "桌面未找到快捷方式，已自动创建：$lnk"
    } catch {
        Write-Warning "创建桌面快捷方式失败（不影响启动）：$_"
    }
}

# ---------- 主体流程 ----------
Install-DesktopShortcut

$backendUp = Test-PortOpen $BackendPort
$frontendUp = Test-PortOpen $FrontendPort

if ($backendUp -and $frontendUp) {
    Write-Step "前后端都已在运行，直接打开浏览器。"
    Start-Process $FrontendUrl
    exit 0
}

if (-not $backendUp) {
    Write-Step "启动后端 Flask(:$BackendPort) ...（窗口标题：MusicRate 后端 :5000）"
    $env:PYTHONIOENCODING = 'utf-8'
    Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title MusicRate 后端 :5000 & portable\python\python.exe backend\run.py') -WorkingDirectory $root
}
if (-not $frontendUp) {
    Write-Step "启动前端 npm(:$FrontendPort) ...（窗口标题：MusicRate 前端 :8080）"
    Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title MusicRate 前端 :8080 & npm run serve') -WorkingDirectory (Join-Path $root 'frontend')
}

Write-Step "等待服务就绪（最多 120 秒）..."
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    if (-not $backendUp) { $backendUp = Test-PortOpen $BackendPort }
    if (-not $frontendUp) { $frontendUp = Test-PortOpen $FrontendPort }
    if ($backendUp -and $frontendUp) { break }
    Start-Sleep -Milliseconds 700
}

if ($backendUp) {
    Write-Step "后端就绪 http://localhost:$BackendPort"
} else {
    Write-Warning "后端 $BackendPort 端口 120 秒内未就绪，请查看『MusicRate 后端』窗口的报错。"
}
if ($frontendUp) {
    Write-Step "前端就绪 $FrontendUrl"
} else {
    Write-Warning "前端 $FrontendPort 端口 120 秒内未就绪，请查看『MusicRate 前端』窗口的报错。"
}

# 自动打开浏览器（优先前端页面）
if ($frontendUp) {
    Start-Process $FrontendUrl
} elseif ($backendUp) {
    Start-Process "http://localhost:$BackendPort"
}