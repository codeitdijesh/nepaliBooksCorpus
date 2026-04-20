$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

$manifestFull = "data/manifest_full.jsonl"
$manifestFirst1000 = "data/manifest_first1000.jsonl"
$manifestFirst1000Summary = "data/manifest_first1000_summary.json"
$probeFirst1000 = "data/probe_first1000.jsonl"
$probeFirst1000Summary = "data/probe_first1000_summary.json"
$fetchFirst1000 = "data/fetch_first1000.jsonl"
$downloadDir = "data/pdfs_first1000"

Write-Output "run_first_1000_download start workspace=$workspace"

python -u -m epustakalaya_corpus crawl-manifest `
  --page-start 1 `
  --page-end 90 `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $manifestFull `
  --resume

$first1000 = Get-Content $manifestFull -Encoding utf8 | Select-Object -First 1000
if ($first1000.Count -lt 1000) {
  throw "Only $($first1000.Count) manifest rows available after crawl; expected at least 1000."
}
$first1000 | Set-Content -Path $manifestFirst1000 -Encoding utf8
Write-Output "manifest_first1000 ready rows=1000 path=$manifestFirst1000"

python -u -m epustakalaya_corpus summarize-manifest `
  --manifest $manifestFirst1000 `
  --output $manifestFirst1000Summary

python -u -m epustakalaya_corpus probe-access `
  --manifest $manifestFirst1000 `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output $probeFirst1000 `
  --resume

python -u -m epustakalaya_corpus summarize-probe `
  --probe $probeFirst1000 `
  --output $probeFirst1000Summary

python -u -m epustakalaya_corpus fetch-pdfs `
  --probe $probeFirst1000 `
  --download-dir $downloadDir `
  --delay-seconds 0.75 `
  --timeout-seconds 120 `
  --output $fetchFirst1000 `
  --resume

Write-Output "run_first_1000_download done"
