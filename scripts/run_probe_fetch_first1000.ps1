$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

Write-Output "run_probe_fetch_first1000 start workspace=$workspace"

python -u -m epustakalaya_corpus probe-access `
  --manifest data/manifest_first1000.jsonl `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output data/probe_first1000.jsonl `
  --resume

python -u -m epustakalaya_corpus summarize-probe `
  --probe data/probe_first1000.jsonl `
  --output data/probe_first1000_summary.json

python -u -m epustakalaya_corpus fetch-pdfs `
  --probe data/probe_first1000.jsonl `
  --download-dir data/pdfs_first1000 `
  --delay-seconds 0.75 `
  --timeout-seconds 120 `
  --output data/fetch_first1000.jsonl `
  --resume

Write-Output "run_probe_fetch_first1000 done"
