# 停掉临时公网隧道
Get-Process ssh -ErrorAction SilentlyContinue | Where-Object {
    # 只杀连 serveo.net / localhost.run / pinggy 的隧道进程，不动别的 ssh
    try { $_.CommandLine -match 'serveo|localhost\.run|pinggy' } catch { $false }
} | ForEach-Object {
    Write-Host "停止隧道进程 PID $($_.Id)" -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force
}
Write-Host "完成。" -ForegroundColor Green
