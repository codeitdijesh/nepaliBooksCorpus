$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

Write-Output "run_full_pustakalaya_metadata start workspace=$workspace"

python -u -m epustakalaya_corpus crawl-manifest `
  --page-start 1 `
  --page-end 692 `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output data/manifest_full.jsonl `
  --resume

python -u -m epustakalaya_corpus summarize-manifest `
  --manifest data/manifest_full.jsonl `
  --output data/manifest_full_summary.json

python -u -m epustakalaya_corpus probe-access `
  --manifest data/manifest_full.jsonl `
  --delay-seconds 0.75 `
  --timeout-seconds 45 `
  --output data/probe_full.jsonl `
  --resume

python -u -m epustakalaya_corpus summarize-probe `
  --probe data/probe_full.jsonl `
  --output data/probe_full_summary.json

Write-Output "run_full_pustakalaya_metadata done"
