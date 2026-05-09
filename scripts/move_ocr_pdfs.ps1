$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
Set-Location $workspace

$fullFetchPath = "data\fetch_no_english.jsonl"
$ocrFetchPath = "data\fetch_no_english_needs_ocr.jsonl"
$sourceDir = Join-Path $workspace "data\pdfs_no_english"
$targetDir = Join-Path $workspace "data\pdfs_no_english_needs_ocr"

function Read-Jsonl([string]$PathValue) {
  $rows = New-Object System.Collections.Generic.List[object]
  foreach ($line in [System.IO.File]::ReadLines((Resolve-Path $PathValue).Path)) {
    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }
    $rows.Add(($line | ConvertFrom-Json))
  }
  return $rows
}

function Write-Jsonl([string]$PathValue, [System.Collections.IEnumerable]$Rows) {
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $writer = New-Object System.IO.StreamWriter([System.IO.Path]::GetFullPath($PathValue), $false, $utf8NoBom)
  try {
    foreach ($row in $Rows) {
      $writer.WriteLine(($row | ConvertTo-Json -Compress -Depth 10))
    }
  }
  finally {
    $writer.Dispose()
  }
}

function Assert-PathUnder([string]$CandidatePath, [string]$ExpectedRoot) {
  $candidateFull = [System.IO.Path]::GetFullPath($CandidatePath)
  $rootFull = [System.IO.Path]::GetFullPath($ExpectedRoot)
  if (-not $candidateFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to move path outside expected root. candidate=$candidateFull root=$rootFull"
  }
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$ocrRows = Read-Jsonl $ocrFetchPath
$fullRows = Read-Jsonl $fullFetchPath

$ocrById = @{}
foreach ($row in $ocrRows) {
  $ocrById[$row.doc_id] = $true
}

$moved = 0
$alreadyInTarget = 0
$missing = 0
$updatedFullRows = 0

foreach ($row in $ocrRows) {
  $currentRelative = [string]$row.pdf_path
  if ([string]::IsNullOrWhiteSpace($currentRelative)) {
    continue
  }

  $currentFull = Join-Path $workspace $currentRelative
  $fileName = [System.IO.Path]::GetFileName($currentFull)
  $targetFull = Join-Path $targetDir $fileName
  $targetRelative = "data\pdfs_no_english_needs_ocr\$fileName"

  Assert-PathUnder $targetFull $targetDir

  if ($currentFull.Equals($targetFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    $alreadyInTarget += 1
  }
  elseif (Test-Path -LiteralPath $currentFull) {
    Assert-PathUnder $currentFull $sourceDir
    Move-Item -LiteralPath $currentFull -Destination $targetFull -Force
    $moved += 1
  }
  elseif (Test-Path -LiteralPath $targetFull) {
    $alreadyInTarget += 1
  }
  else {
    $missing += 1
  }

  $row.pdf_path = $targetRelative
  if ($null -ne $row.path) {
    $row.path = $targetRelative
  }
}

foreach ($row in $fullRows) {
  if (-not $ocrById.ContainsKey($row.doc_id)) {
    continue
  }
  $fileName = [System.IO.Path]::GetFileName([string]$row.pdf_path)
  $targetRelative = "data\pdfs_no_english_needs_ocr\$fileName"
  $row.pdf_path = $targetRelative
  if ($null -ne $row.path) {
    $row.path = $targetRelative
  }
  $updatedFullRows += 1
}

Write-Jsonl $ocrFetchPath $ocrRows
Write-Jsonl $fullFetchPath $fullRows

Write-Output "move_ocr_pdfs done moved=$moved already_in_target=$alreadyInTarget missing=$missing updated_ocr_rows=$($ocrRows.Count) updated_full_rows=$updatedFullRows target_dir=$targetDir"
