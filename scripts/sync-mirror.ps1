# scripts/sync-mirror.ps1
# 一键把 main 分支 + 全部 tags 推送到 GitHub(origin) 与 Gitee(gitee) 两个远端。
# 用法：
#   powershell -NoProfile -File scripts/sync-mirror.ps1             # 检查 + dry-run + 实际推送
#   powershell -NoProfile -File scripts/sync-mirror.ps1 -NoPush     # 只检查 + dry-run，不推送
#   powershell -NoProfile -File scripts/sync-mirror.ps1 -SkipChecks # 跳过发布前检查（不推荐）
param(
  [switch]$SkipChecks,
  [switch]$NoPush
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Info($m) { Write-Host $m }
function Warn($m) { Write-Host "[警告] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[失败] $m" -ForegroundColor Red; exit 1 }
function Ok($m)   { Write-Host "[通过] $m" -ForegroundColor Green }

# 跑一条 git 命令，返回 @{ code; out }
function Invoke-Git([string[]]$cmdArgs) {
  $out = & git @cmdArgs 2>&1 | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { $_ }
  }
  return @{ code = $LASTEXITCODE; out = ($out | Out-String).Trim() }
}

# 把 git 报错翻译成人话
function Explain([string]$text) {
  if ($text -match "not found|does not appear to be a git|ERROR: Repository") {
    return "远端仓库不存在：请先去 GitHub / Gitee 建一个空的 ec-hot 仓库（不要勾选 README / .gitignore / license）。"
  }
  if ($text -match "Permission denied \(publickey\)|Could not read from remote|no such identity|Host key verification failed") {
    return "SSH 认证失败：确认 C:\Users\19024\.ssh\id_ed25519_echot 的公钥已加到两个平台，且 ~/.ssh/config 指向了它。"
  }
  if ($text -match "Could not resolve host|Failed to connect|timed out|unable to access|Network is unreachable") {
    return "网络不通：检查能否访问 github.com / gitee.com（可能需要代理）。"
  }
  if ($text -match "rejected|non-fast-forward|fetch first") {
    return "远端有本地没有的提交：先 git pull --rebase 对应远端，再推送。"
  }
  return "推送失败，原始输出见上方。"
}

Info "== 仓库双远端同步（origin=GitHub, gitee=Gitee）=="
Info "仓库根目录：$repoRoot"

# ---- 0. 前置 ----
if (-not (Test-Path "$repoRoot\.git")) { Die "当前目录不是 git 仓库：$repoRoot" }
$branch = (Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD')).out
if ($branch -ne 'main') { Die "当前分支是 '$branch'，脚本只推 main。请先 git checkout main。" }
Info "当前分支：main"

# ---- 1. 发布前检查 ----
if (-not $SkipChecks) {
  Info "`n[1/4] 发布前检查"

  $tracked = (Invoke-Git @('ls-files')).out -split "[\r\n]+" | Where-Object { $_ }
  $badEnv = $tracked | Where-Object { $_ -like '*.env*' -and $_ -ne '.env.example' }
  if ($badEnv) { Die "发现误提交的 .env 文件：$($badEnv -join ', ')" }
  Ok "没有 .env 被提交（.env.example 模板除外）"

  $badPaths = $tracked | Where-Object { $_ -match '^(state|logs|node_modules)/' -or $_ -like '*.log' }
  if ($badPaths) { Die "发现不应提交的目录/日志：$($badPaths -join ', ')" }
  Ok "没有 state/、logs/、node_modules/、*.log 被提交"

  $secretHit = (Invoke-Git @('grep', '-n', '-I', '-E', '-e', '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}')).out
  if ($secretHit) { Die "跟踪文件里疑似有密钥，请清理后再推：`n$secretHit" }
  Ok "未发现明显密钥/令牌"
} else {
  Warn "已跳过发布前检查（-SkipChecks）"
}

# ---- 2. 将要推送的提交 ----
Info "`n[2/4] 将要推送的提交（main）"
$originCheck = Invoke-Git @('rev-parse', '--verify', 'origin/main')
if ($originCheck.code -eq 0) {
  $commits = (Invoke-Git @('log', '--oneline', 'origin/main..HEAD')).out
  if ($commits) { Info $commits } else { Info "（没有新提交：origin/main 与本地一致）" }
} else {
  Info "首次推送：origin 还没有分支，将推送 main 上的最近提交："
  Info ((Invoke-Git @('log', '--oneline', '-n', '10')).out)
}

# ---- 3. dry-run ----
Info "`n[3/4] dry-run（不实际推送）"
foreach ($remote in @('origin', 'gitee')) {
  $r = Invoke-Git @('push', '--dry-run', $remote, 'main', '--tags')
  if ($r.code -eq 0) {
    Ok "$remote dry-run 成功：`n$($r.out)"
  } else {
    Warn "$remote dry-run 未通过：$($r.out)"
    Warn (Explain $r.out)
  }
}

# ---- 4. 实际推送 ----
if ($NoPush) {
  Info "`n[4/4] 已指定 -NoPush，到此为止。"
  exit 0
}

Info "`n[4/4] 实际推送"
$allOk = $true
foreach ($remote in @('origin', 'gitee')) {
  $r = Invoke-Git @('push', $remote, 'main', '--tags')
  if ($r.code -eq 0) {
    Ok "$remote 推送成功：`n$($r.out)"
  } else {
    $allOk = $false
    Die "$remote 推送失败：$($r.out)`n$(Explain $r.out)"
  }
}
if ($allOk) {
  Info "`n全部完成。两个平台的 main 与 tags 已一致。"
}
