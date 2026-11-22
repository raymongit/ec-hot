# 开放局域网访问（需要管理员权限，只需跑一次）
#
# 用法：右键「使用 PowerShell 运行」，或在管理员 PowerShell 里执行：
#   powershell -ExecutionPolicy Bypass -File .\open-lan.ps1
#
# 原理：站点跑在 WSL2 的 Docker 里，WSL2 默认 NAT 模式，只有 Windows 本机 localhost
#      能转发到容器端口。要让手机/平板访问，需要：
#      1) netsh portproxy 把 0.0.0.0:3000 转发到 127.0.0.1:3000
#      2) 防火墙放行 3000 入站

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "需要管理员权限，正在弹出 UAC 授权窗口……" -ForegroundColor Cyan
    try {
        Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
        ) | Out-Null
    } catch {
        Write-Host "提权被取消。请右键这个文件 -> 使用 PowerShell 运行，或手动以管理员身份执行。" -ForegroundColor Red
        pause
    }
    exit
}

$port = 3000
Write-Host "1/3 配置端口转发 0.0.0.0:$port -> 127.0.0.1:$port" -ForegroundColor Cyan
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=127.0.0.1 connectport=$port | Out-Null

Write-Host "2/3 放行防火墙入站 $port" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "EC-HOT $port" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "EC-HOT $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow -Profile Private,Domain | Out-Null

Write-Host "3/3 验证" -ForegroundColor Cyan
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notmatch 'WSL|Loopback|vEthernet'
} | Select-Object -First 1).IPAddress

if ($ip) {
    try {
        $r = Invoke-WebRequest "http://${ip}:$port" -TimeoutSec 10 -UseBasicParsing
        Write-Host "成功：http://${ip}:$port -> $($r.StatusCode)" -ForegroundColor Green
        Write-Host "手机连同一个 WiFi，打开 http://${ip}:$port 即可。" -ForegroundColor Green
    } catch {
        Write-Host "端口转发已配置，但本机自测失败：$($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "可能原因：容器没起（先跑 wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Users/19024/Documents/ecommerce-hot/restart-site.sh）" -ForegroundColor Yellow
    }
} else {
    Write-Host "没找到内网 IP，请用 ipconfig 自己确认。" -ForegroundColor Yellow
}
