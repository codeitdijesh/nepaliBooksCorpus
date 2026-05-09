param(
  [int]$TargetPages = 692
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

function Get-JsonlRowCount([string]$PathValue) {
  if (-not (Test-Path $PathValue)) {
    return 0
  }
  $path = (Resolve-Path $PathValue).Path
  $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
  try {
    $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8, $true)
    $count = 0
    while (($null -ne $reader.ReadLine())) {
      $count += 1
    }
    return $count
  }
  finally {
    if ($reader) { $reader.Dispose() }
    $stream.Dispose()
  }
}

function Get-JsonlLastObject([string]$PathValue) {
  if (-not (Test-Path $PathValue)) {
    return $null
  }
  $path = (Resolve-Path $PathValue).Path
  $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
  try {
    $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8, $true)
    $tail = New-Object System.Collections.Generic.Queue[string]
    while (-not $reader.EndOfStream) {
      $line = $reader.ReadLine()
      if ($tail.Count -ge 5) {
        [void]$tail.Dequeue()
      }
      $tail.Enqueue($line)
    }

    $tailLines = @($tail.ToArray())
    [array]::Reverse($tailLines)
    foreach ($line in $tailLines) {
      if ([string]::IsNullOrWhiteSpace($line)) {
        continue
      }
      try {
        return $line | ConvertFrom-Json
      }
      catch {
        continue
      }
    }
    return $null
  }
  finally {
    if ($reader) { $reader.Dispose() }
    $stream.Dispose()
  }
}

function Get-DirectorySummary([string]$PathValue) {
  if (-not (Test-Path $PathValue)) {
    return [pscustomobject]@{
      Count = 0
      Bytes = [int64]0
    }
  }
  $files = Get-ChildItem $PathValue -File -ErrorAction SilentlyContinue
  $bytes = ($files | Measure-Object -Property Length -Sum).Sum
  if ($null -eq $bytes) {
    $bytes = 0
  }
  return [pscustomobject]@{
    Count = $files.Count
    Bytes = [int64]$bytes
  }
}

function Format-Bytes([int64]$Bytes) {
  $value = [double]$Bytes
  $units = @("B", "KB", "MB", "GB", "TB")
  $index = 0
  while ($value -ge 1024 -and $index -lt ($units.Count - 1)) {
    $value = $value / 1024
    $index += 1
  }
  return "{0:N2} {1}" -f $value, $units[$index]
}

function Format-Percent([int]$Numerator, [int]$Denominator) {
  if ($Denominator -le 0) {
    return "n/a"
  }
  return "{0:P1}" -f ($Numerator / [double]$Denominator)
}

function Get-RunInfo {
  $stageRanks = @{
    "idle" = 0
    "crawl-manifest" = 1
    "filter-manifest" = 2
    "probe-access" = 3
    "fetch-pdfs" = 4
    "split-fetch-by-ocr" = 5
    "python-running" = 6
  }

  $scriptProcesses = @(Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*run_full_no_english_download.ps1*" } |
    Sort-Object CreationDate)

  $runs = @()
  foreach ($scriptProcess in $scriptProcesses) {
    $pythonProcess = Get-CimInstance Win32_Process |
      Where-Object { $_.ParentProcessId -eq $scriptProcess.ProcessId -and $_.Name -eq "python.exe" } |
      Sort-Object CreationDate -Descending |
      Select-Object -First 1

    $stage = "idle"
    if ($pythonProcess) {
      foreach ($stageName in @("crawl-manifest", "filter-manifest", "probe-access", "fetch-pdfs", "split-fetch-by-ocr")) {
        if ($pythonProcess.CommandLine -like "*$stageName*") {
          $stage = $stageName
          break
        }
      }
      if ($stage -eq "idle") {
        $stage = "python-running"
      }
    }

    $runs += [pscustomobject]@{
      ScriptProcess = $scriptProcess
      PythonProcess = $pythonProcess
      Stage = $stage
      StageRank = $stageRanks[$stage]
    }
  }

  $primaryRun = $runs |
    Sort-Object @{ Expression = "StageRank"; Descending = $true }, @{ Expression = { $_.ScriptProcess.CreationDate }; Descending = $false } |
    Select-Object -First 1

  return [pscustomobject]@{
    Runs = $runs
    ScriptProcess = if ($primaryRun) { $primaryRun.ScriptProcess } else { $null }
    PythonProcess = if ($primaryRun) { $primaryRun.PythonProcess } else { $null }
    Stage = if ($primaryRun) { $primaryRun.Stage } else { "idle" }
    MultipleRuns = ($runs.Count -gt 1)
  }
}

$manifestFull = "data/manifest_full.jsonl"
$manifestFiltered = "data/manifest_no_english.jsonl"
$probeFiltered = "data/probe_no_english.jsonl"
$fetchFiltered = "data/fetch_no_english.jsonl"
$downloadDir = "data/pdfs_no_english"
$goodPdfInventory = "data/fetch_no_english_good.jsonl"
$ocrPdfInventory = "data/fetch_no_english_needs_ocr.jsonl"

$runInfo = Get-RunInfo
$manifestRows = Get-JsonlRowCount $manifestFull
$manifestFilteredRows = Get-JsonlRowCount $manifestFiltered
$probeRows = Get-JsonlRowCount $probeFiltered
$fetchRows = Get-JsonlRowCount $fetchFiltered
$goodRows = Get-JsonlRowCount $goodPdfInventory
$ocrRows = Get-JsonlRowCount $ocrPdfInventory
$downloads = Get-DirectorySummary $downloadDir

$manifestLast = Get-JsonlLastObject $manifestFull
$manifestLastPage = 0
$manifestLastTimestamp = ""
if ($manifestLast) {
  if ($manifestLast.crawl_page) {
    $manifestLastPage = [int]$manifestLast.crawl_page
  }
  if ($manifestLast.crawl_timestamp) {
    $manifestLastTimestamp = [string]$manifestLast.crawl_timestamp
  }
}

$activeState = if ($runInfo.ScriptProcess) { "running" } else { "not_running" }
$scriptStarted = if ($runInfo.ScriptProcess) { [string]$runInfo.ScriptProcess.CreationDate } else { "n/a" }
$pythonStarted = if ($runInfo.PythonProcess) { [string]$runInfo.PythonProcess.CreationDate } else { "n/a" }
$lastManifestWrite = if (Test-Path $manifestFull) { (Get-Item $manifestFull).LastWriteTime } else { $null }
$lastManifestWriteText = if ($lastManifestWrite) { [string]$lastManifestWrite } else { "n/a" }
$crawlComplete = ($manifestRows -gt 0) -and ($runInfo.Stage -ne "crawl-manifest") -and (($manifestFilteredRows -gt 0) -or ($probeRows -gt 0) -or ($fetchRows -gt 0))
$crawlStatus = if ($crawlComplete) { "complete" } else { Format-Percent $manifestLastPage $TargetPages }

Write-Output ("[{0}] run_status={1} active_stage={2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $activeState, $runInfo.Stage)
if ($runInfo.MultipleRuns) {
  Write-Output ("warning: multiple_run_processes={0}" -f $runInfo.Runs.Count)
}
if ($runInfo.ScriptProcess) {
  Write-Output ("script_process: pid={0} started={1}" -f $runInfo.ScriptProcess.ProcessId, $scriptStarted)
}
if ($runInfo.PythonProcess) {
  Write-Output ("python_process: pid={0} started={1}" -f $runInfo.PythonProcess.ProcessId, $pythonStarted)
}
Write-Output ("manifest_full: rows={0} last_page={1} configured_target_pages={2} crawl_status={3} last_row_timestamp={4} last_write={5}" -f $manifestRows, $manifestLastPage, $TargetPages, $crawlStatus, $manifestLastTimestamp, $lastManifestWriteText)
Write-Output ("manifest_no_english: rows={0}" -f $manifestFilteredRows)
Write-Output ("probe_no_english: rows={0}" -f $probeRows)
Write-Output ("fetch_no_english: rows={0}" -f $fetchRows)
Write-Output ("pdfs_no_english: files={0} size={1}" -f $downloads.Count, (Format-Bytes $downloads.Bytes))
Write-Output ("ocr_split: good_rows={0} needs_ocr_rows={1}" -f $goodRows, $ocrRows)
