# 电商 HOT 公网隧道守护进程
#
# 作用：维持 serveo SSH 隧道，断了自动重连；把当前公网地址写到固定文件里。
#   当前地址：%TEMP%\echot-public-url.txt
#
# 由 Startup 里的 ECHOT-Tunnel.vbs 在登录时启动，也可手动：
#   powershell -WindowStyle Hidden -File "C:\Users\19024\Documents\ecommerce-hot\AIHOT\tools\tunnel-supervisor.ps1"

param([int]$Port = 3001)

$urlFile  = Join-Path $env:TEMP "echot-public-url.txt"
$outFile  = Join-Path $env:TEMP "echot-ssh.out"
$errFile  = Join-Path $env:TEMP "echot-ssh.err"
$logFile  = Join-Path $env:TEMP "echot-tunnel.log"

function Write-Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Add-Content -Path $logFile -Encoding UTF8
}

Write-Log "supervisor 启动，端口 $Port"

while ($true) {
    try {
        Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
        $p = Start-Process -FilePath "ssh.exe" `
            -ArgumentList '-T', '-o', 'StrictHostKeyChecking=accept-new',
                          '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=3',
                          '-o', 'ExitOnForwardFailure=yes',
                          '-R', "80:localhost:$Port", 'serveo.net' `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile `
            -PassThru -WindowStyle Hidden

        Write-Log "ssh 已启动 pid=$($p.Id)"

        # 等地址出现（最多 40 秒）
        $url = $null
        for ($i = 0; $i -lt 40; $i++) {
            Start-Sleep -Seconds 1
            $txt = (Get-Content $outFile, $errFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue) -join "`n"
            if ($txt -match 'https://[a-z0-9\-]+\.serveousercontent\.com') {
                $url = $Matches[0]
                $url | Set-Content -Path $urlFile -Encoding UTF8
                Write-Log "公网地址: $url"
                break
            }
            if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) { break }
        }

        if (-not $url) { Write-Log "没拿到地址，准备重试" }

        Wait-Process -Id $p.Id -ErrorAction SilentlyContinue
        Write-Log "ssh 退出，5 秒后重连"
    } catch {
        Write-Log "异常: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 5
}
