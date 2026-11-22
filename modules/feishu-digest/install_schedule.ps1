# 注册 Windows 计划任务：每天定时跑「电商 HOT 早报」并推送到飞书
#
#   .\install_schedule.ps1                 # 默认每天 09:00
#   .\install_schedule.ps1 -Time 07:30     # 改时间
#   .\install_schedule.ps1 -Remove         # 卸载任务

param(
    [string]$Time = "09:00",
    [string]$TaskName = "ECHOT-Daily-Feishu",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\19024\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\pythonw.exe"
$script = Join-Path $root "aihot.py"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F 2>$null
    Write-Host "已删除计划任务 $TaskName" -ForegroundColor Yellow
    return
}

if (-not (Test-Path $python)) { Write-Host "找不到 pythonw.exe：$python" -ForegroundColor Red; return }
if (-not (Test-Path $script)) { Write-Host "找不到 aihot.py：$script" -ForegroundColor Red; return }
if ($Time -notmatch '^\d{2}:\d{2}$') { Write-Host "时间格式应为 HH:mm，例如 09:00" -ForegroundColor Red; return }

$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
# 今天还没到点就从今天开始，过了点就从明天开始
$clock = [TimeSpan]::Parse($Time)
$base = (Get-Date).Date
if ((Get-Date).TimeOfDay -ge $clock) { $base = $base.AddDays(1) }
$start = $base.ToString("yyyy-MM-dd") + "T" + $Time + ":00"

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>电商 HOT 每日早报：抓取电商信源，精选后推送到飞书</Description>
    <URI>\$TaskName</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$start</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$sid</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$python</Command>
      <Arguments>"$script"</Arguments>
      <WorkingDirectory>$root</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$tmp = Join-Path $env:TEMP "echot-task.xml"
$xml | Out-File -FilePath $tmp -Encoding Unicode

schtasks /Create /TN $TaskName /XML $tmp /F | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "注册失败（exit $LASTEXITCODE）" -ForegroundColor Red; return }

Remove-Item $tmp -Force
Write-Host "已注册计划任务：$TaskName，每天 $Time 运行" -ForegroundColor Green
Write-Host "试跑一次：schtasks /Run /TN $TaskName"
Write-Host "查看状态：schtasks /Query /TN $TaskName /V /FO LIST"
