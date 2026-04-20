$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

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

Write-Output "run_full_no_english_download start workspace=$workspace"

python -u -m epustakalaya_corpus crawl-manifest `
  --page-start 1 `
  --page-end 692 `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $manifestFull `
  --resume

python -u -m epustakalaya_corpus filter-manifest `
  --manifest $manifestFull `
  --output $manifestFiltered `
  --summary $manifestFilteredSummary `
  --exclude-english

python -u -m epustakalaya_corpus probe-access `
  --manifest $manifestFiltered `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $probeFiltered `
  --resume

python -u -m epustakalaya_corpus summarize-probe `
  --probe $probeFiltered `
  --output $probeFilteredSummary

python -u -m epustakalaya_corpus fetch-pdfs `
  --probe $probeFiltered `
  --download-dir $downloadDir `
  --delay-seconds 0.75 `
  --timeout-seconds 120 `
  --output $fetchFiltered `
  --resume

python -u -m epustakalaya_corpus split-fetch-by-ocr `
  --fetch $fetchFiltered `
  --manifest $manifestFiltered `
  --good-output $goodPdfInventory `
  --ocr-output $ocrPdfInventory `
  --summary $ocrSplitSummary `
  --min-chars-per-page 50

Write-Output "run_full_no_english_download done"
