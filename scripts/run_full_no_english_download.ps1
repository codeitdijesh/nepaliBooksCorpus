param(
  [int]$PageStart = 1,
  [int]$PageEnd = 692
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

$logDir = Join-Path $workspace "data\logs"
$logPath = Join-Path $logDir "run_full_no_english_download.log"

$manifestFull = "data/manifest_full.jsonl"
$manifestFiltered = "data/manifest_no_english.jsonl"
$manifestFilteredSummary = "data/manifest_no_english_summary.json"
$probeFiltered = "data/probe_no_english.jsonl"
$probeFilteredSummary = "data/probe_no_english_summary.json"
$fetchFiltered = "data/fetch_no_english.jsonl"
$downloadDir = "data/pdfs_no_english"
$goodPdfInventory = "data/fetch_no_english_good.jsonl"
$ocrPdfInventory = "data/fetch_no_english_needs_ocr.jsonl"
$ocrSplitSummary = "data/fetch_no_english_ocr_split_summary.json"

function Write-Stage([string]$Message) {
  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Write-Output "[$timestamp] $Message"
}

function Write-StatusSnapshot([string]$Label) {
  $statusScript = Join-Path $PSScriptRoot "show_no_english_status.ps1"
  if (-not (Test-Path $statusScript)) {
    return
  }
  Write-Stage "status_snapshot label=$Label"
  & $statusScript | ForEach-Object { Write-Output $_ }
}

function Assert-LastExitCode([string]$StepName) {
  if ($LASTEXITCODE -ne 0) {
    throw "$StepName failed with exit code $LASTEXITCODE"
  }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Start-Transcript -Path $logPath -Append | Out-Null

try {
Write-Stage "run_full_no_english_download start workspace=$workspace log=$logPath page_start=$PageStart page_end=$PageEnd"
Write-StatusSnapshot "before_crawl"

Write-Stage "stage=crawl-manifest start output=$manifestFull page_start=$PageStart page_end=$PageEnd"
python -u -m epustakalaya_corpus crawl-manifest `
  --page-start $PageStart `
  --page-end $PageEnd `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $manifestFull `
  --resume
Assert-LastExitCode "crawl-manifest"

Write-StatusSnapshot "after_crawl"

Write-Stage "stage=filter-manifest start input=$manifestFull output=$manifestFiltered summary=$manifestFilteredSummary"
python -u -m epustakalaya_corpus filter-manifest `
  --manifest $manifestFull `
  --output $manifestFiltered `
  --summary $manifestFilteredSummary `
  --exclude-english
Assert-LastExitCode "filter-manifest"

Write-StatusSnapshot "after_filter"

Write-Stage "stage=probe-access start manifest=$manifestFiltered output=$probeFiltered"
python -u -m epustakalaya_corpus probe-access `
  --manifest $manifestFiltered `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $probeFiltered `
  --resume
Assert-LastExitCode "probe-access"

Write-Stage "stage=summarize-probe start probe=$probeFiltered output=$probeFilteredSummary"
python -u -m epustakalaya_corpus summarize-probe `
  --probe $probeFiltered `
  --output $probeFilteredSummary
Assert-LastExitCode "summarize-probe"

Write-StatusSnapshot "after_probe"

Write-Stage "stage=fetch-pdfs start probe=$probeFiltered output=$fetchFiltered download_dir=$downloadDir"
python -u -m epustakalaya_corpus fetch-pdfs `
  --probe $probeFiltered `
  --download-dir $downloadDir `
  --delay-seconds 0.75 `
  --timeout-seconds 120 `
  --output $fetchFiltered `
  --resume
Assert-LastExitCode "fetch-pdfs"

Write-StatusSnapshot "after_fetch"

Write-Stage "stage=split-fetch-by-ocr start fetch=$fetchFiltered good_output=$goodPdfInventory ocr_output=$ocrPdfInventory"
python -u -m epustakalaya_corpus split-fetch-by-ocr `
  --fetch $fetchFiltered `
  --manifest $manifestFiltered `
  --good-output $goodPdfInventory `
  --ocr-output $ocrPdfInventory `
  --summary $ocrSplitSummary `
  --min-chars-per-page 50
Assert-LastExitCode "split-fetch-by-ocr"

Write-StatusSnapshot "after_ocr_split"
Write-Stage "run_full_no_english_download done"
}
finally {
  Stop-Transcript | Out-Null
}
