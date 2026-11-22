# 启动临时公网隧道（serveo.net，SSH 反向隧道，无需安装任何东西）
#
#   .\start-tunnel.ps1
#
# 前置：站点与 Caddy 边缘已启动（3001 端口在监听）
#   wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Users/19024/Documents/ecommerce-hot/restart-site.sh
#   wsl -d Ubuntu-24.04 -u root -- bash -lc "cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT && docker compose -f docker-compose.yml -f docker-compose.public.yml up -d edge"
#
# 停止：关掉这个窗口，或运行 .\stop-tunnel.ps1
# 注意：免费版 URL 每次重启都会变；页面可能先显示 serveo 的提示页，点继续即可。

param([int]$Port = 3001)

$ErrorActionPreference = "Stop"
$log = Join-Path $env:TEMP "echot-tunnel.log"
Remove-Item $log -Force -ErrorAction SilentlyContinue

Write-Host "正在建立 SSH 反向隧道（localhost:$Port -> serveo.net）..." -ForegroundColor Cyan
Write-Host "连上之后会打印一个 https://xxx.serveousercontent.com 地址。" -ForegroundColor Gray

& ssh.exe -T -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes -R "80:localhost:$Port" serveo.net 2>&1 |
    ForEach-Object {
        $_ | Tee-Object -FilePath $log -Append
        if ($_ -match 'https://[a-z0-9\-]+\.serveousercontent\.com') {
            Write-Host ""
            Write-Host "公网地址：$($Matches[0])" -ForegroundColor Green
            Write-Host "（保持这个窗口开着，关掉就断）" -ForegroundColor Yellow
        }
    }
