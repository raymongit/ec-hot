# 把 DSH 侧的进展同步到 Multica（一条命令）
#
#   .\sync-to-multica.ps1                 # 默认同步到 RAY-50
#   .\sync-to-multica.ps1 -Issue RAY-57   # 同步到指定 issue
#
# 原理：Multica 不会自动感知 DSH 会话里的工作，只有写进 issue 的内容才算「同步」。
#      本脚本把同目录的 PROGRESS.md 作为评论贴到指定 issue，agent 下次运行时能读到。

param(
    [string]$Issue = "RAY-50",
    [string]$File = "PROGRESS.md"
)

$ErrorActionPreference = "Stop"
$mc = "C:\Users\19024\.multica\bin\multica.exe"
$path = Join-Path $PSScriptRoot $File

if (-not (Test-Path $mc)) { Write-Host "找不到 multica CLI：$mc" -ForegroundColor Red; return }
if (-not (Test-Path $path)) { Write-Host "找不到 $path" -ForegroundColor Red; return }

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "同步 $File -> $Issue （$stamp）" -ForegroundColor Cyan

& $mc issue comment add $Issue --content-file $path --allow-external-file --output json | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "已同步。打开 Multica 的 $Issue 就能看到这条评论。" -ForegroundColor Green
} else {
    Write-Host "同步失败（exit $LASTEXITCODE），检查 multica 登录状态" -ForegroundColor Red
}
