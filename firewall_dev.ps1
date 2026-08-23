# =====================================================================
# MusicRate 安全防火墙配置脚本（必须以管理员身份运行）
#
# 背景：之前为了能打开 localhost 把三个防火墙（Domain/Private/Public）
#      全部关闭，非常不安全。本脚本在【防火墙全程开启】的前提下，
#      只放行本机回环地址对 5000/8080 的访问，局域网/公网其他机器
#      一律无法访问，既恢复了 localhost 登录，又不必关闭防火墙。
#
# 用法：在 PowerShell 中执行（会弹 UAC 确认框，点“是”）：
#   powershell -ExecutionPolicy Bypass -File .\firewall_dev.ps1
# 或直接右键“使用 PowerShell 运行”（部分系统不弹 UAC 则需手动提权）
#
# 脚本幂等：可重复执行，旧规则会被自动清理重建。
# 日志输出到本脚本同目录的 firewall_dev_log.txt
#
# 如需允许局域网内手机/其他电脑访问（例如真机调试），可额外执行：
#   New-NetFirewallRule -DisplayName 'MusicRate-LAN' -Direction Inbound `
#     -Protocol TCP -LocalPort 5000,8080 -RemoteAddress LocalSubnet `
#     -Action Allow -Profile Private
# 注意：仅对“专用网络”配置文件生效，公用网络（公共 Wi-Fi）仍被拒。
#
# 注：本文件必须保存为 UTF-8 带 BOM 编码，否则 Windows PowerShell 5.1
#     会按 ANSI 误读导致中文乱码/语法错误。
# =====================================================================
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$logFile = Join-Path $PSScriptRoot 'firewall_dev_log.txt'
function Write-Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Write-Host $line
    Add-Content -LiteralPath $logFile -Value $line
}

"===== MusicRate 防火墙配置 $(Get-Date) =====" | Set-Content -LiteralPath $logFile

# ---------- 1. 打开三个防火墙配置文件 ----------
Set-NetFirewallProfile -Profile Domain, Private, Public -Enabled True
Write-Log '已将 Domain/Private/Public 三个配置文件全部置为【开启】状态'

# ---------- 2. 清理本脚本之前创建的旧规则（保证幂等） ----------
Get-NetFirewallRule -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like 'MusicRate-*' } |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue
Write-Log '已清理旧的 MusicRate-* 防火墙规则'

# ---------- 3. 添加「仅本机回环」放行规则：5000 后端 / 8080 前端 ----------
$loopbackOnly = @('127.0.0.0/8', '::1/128')
New-NetFirewallRule -DisplayName 'MusicRate-Flask-5000-loopback' `
    -Direction Inbound -Protocol TCP -LocalPort 5000 `
    -RemoteAddress $loopbackOnly -Action Allow -Profile Any | Out-Null
New-NetFirewallRule -DisplayName 'MusicRate-Vue-8080-loopback' `
    -Direction Inbound -Protocol TCP -LocalPort 8080 `
    -RemoteAddress $loopbackOnly -Action Allow -Profile Any | Out-Null
Write-Log '已添加规则：仅允许本机(127.0.0.1/::1)访问 TCP 5000 与 8080'

# ---------- 4. 检查历史误创建的 python/node 阻止规则 ----------
# 之前“Windows 防火墙已阻止部分功能”弹窗若点了“取消”，会生成阻止规则，
# 这正是“关了防火墙才能访问 localhost”的常见元凶。
$staleBlocks = foreach ($r in Get-NetFirewallRule -Direction Inbound -Action Block -Enabled True -ErrorAction SilentlyContinue) {
    $prog = $null
    try {
        $prog = ($r | Get-NetFirewallApplicationFilter -ErrorAction Stop).Program
    } catch {
        $prog = $null
    }
    if ($prog -and ($prog -match 'python' -or $prog -match 'node')) {
        [pscustomobject]@{ Name = $r.DisplayName; Program = $prog }
    }
}
if ($staleBlocks) {
    Write-Log "发现 $($staleBlocks.Count) 条 python/node 阻止规则，正在禁用（列表见下）："
    $staleBlocks | ForEach-Object {
        Write-Log ("    阻止规则: {0}  ->  {1}" -f $_.Name, $_.Program)
        Get-NetFirewallRule -DisplayName $_.Name -ErrorAction SilentlyContinue |
            Set-NetFirewallRule -Enabled False -ErrorAction SilentlyContinue
    }
} else {
    Write-Log '未发现 python/node 相关的历史阻止规则'
}

Write-Log '完成。现在可在防火墙开启状态下正常访问 http://localhost:8080 （前端）与 http://localhost:5000 （后端）'

# ---------- 5. 最终状态验证（回显，便于确认） ----------
Write-Log '---- 最终状态 ----'
Get-NetFirewallProfile | Sort-Object Name | ForEach-Object {
    $state = if ($_.Enabled) { '已开启（安全）' } else { '关闭（!!不安全）' }
    Write-Log ("  配置文件 {0}: {1}" -f $_.Name, $state)
}
$created = Get-NetFirewallRule -DisplayName 'MusicRate-*' -ErrorAction SilentlyContinue |
    Sort-Object DisplayName
if ($created) {
    $created | ForEach-Object {
        Write-Log ("  规则 {0} [{1}]" -f $_.DisplayName, $_.Action)
    }
} else {
    Write-Log '  未找到 MusicRate-* 规则（请确认是否以管理员身份运行）'
}