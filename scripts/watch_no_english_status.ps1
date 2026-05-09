param(
  [int]$IntervalSeconds = 30,
  [int]$TargetPages = 692
)

$ErrorActionPreference = "Stop"

$statusScript = Join-Path $PSScriptRoot "show_no_english_status.ps1"

while ($true) {
  & $statusScript -TargetPages $TargetPages
  Write-Output ""
  Start-Sleep -Seconds $IntervalSeconds
}
