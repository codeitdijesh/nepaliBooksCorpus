# Codex Handoff: Fresh Laptop No-English Run

This file is a handoff summary of the current plan and the key decisions from the chat, so another Codex session on a different laptop can continue without reconstructing context.

## Goal

Prepare a fresh-laptop run of the `pustakalaya.org` pipeline that:

- ignores any downloads already present on this laptop
- excludes all English content from the corpus
- downloads the filtered set
- splits downloaded PDFs into:
  - PDFs with usable embedded text (`good`)
  - PDFs that will likely need OCR (`needs_ocr`)

Important: in this session, the full download was **not** run. The workflow was only prepared and verified locally.

## Confirmed Decisions From Chat

- The existing downloaded files on this laptop do not matter.
- The run on the new laptop should start fresh.
- The filter requirement was clarified to: **remove every English content**.
- Nepali content should be kept, including Nepali books that are not being excluded for any other reason.
- The user also wanted the workflow divided into PDFs that are likely OCR-heavy versus PDFs with good native text.
- The user explicitly asked to keep the work at the “script ready” stage, not to actually run the full download here.

## Current Ready-To-Use Script

Primary script for the new laptop:

- `scripts/run_full_no_english_download.ps1`

What it does:

1. Crawls the full manifest.
2. Filters out all English content with `--exclude-english`.
3. Probes access on the filtered manifest.
4. Downloads the filtered PDFs.
5. Splits the fetched PDFs into `good` and `needs_ocr`.

## Important Scope Note

The current fresh-laptop script excludes **all English content**, and that is intentional.

That means:

- English books are removed.
- Nepali content is kept.
- Nepali textbooks are also kept unless a future session explicitly decides otherwise.

If a later session decides to exclude textbooks too, the filter step in the script should add:

```powershell
--exclude-textbooks
```

## Commands and Features Added

### 1. Manifest filtering

CLI entry:

- `python -m epustakalaya_corpus filter-manifest`

Relevant files:

- `epustakalaya_corpus/cli.py`
- `epustakalaya_corpus/pipeline.py`

Useful flags:

- `--exclude-english`
- `--exclude-textbooks`
- `--include-literature`
- `--include-pattern`
- `--exclude-pattern`

### 2. OCR split after download

CLI entry:

- `python -m epustakalaya_corpus split-fetch-by-ocr`

Relevant files:

- `epustakalaya_corpus/cli.py`
- `epustakalaya_corpus/pipeline.py`

What it produces:

- a JSONL inventory of PDFs with native text (`good-output`)
- a JSONL inventory of PDFs likely needing OCR (`ocr-output`)
- a summary JSON

Heuristic:

- each page is checked with PyMuPDF native text extraction
- pages with too little native text are treated as OCR candidates
- each PDF is classified as one of:
  - `native`
  - `mixed`
  - `ocr`

## Current Output Paths Used By The Fresh-Laptop Script

The script `scripts/run_full_no_english_download.ps1` writes to:

- `data/manifest_full.jsonl`
- `data/manifest_no_english.jsonl`
- `data/manifest_no_english_summary.json`
- `data/probe_no_english.jsonl`
- `data/probe_no_english_summary.json`
- `data/fetch_no_english.jsonl`
- `data/pdfs_no_english/`
- `data/fetch_no_english_good.jsonl`
- `data/fetch_no_english_needs_ocr.jsonl`
- `data/fetch_no_english_ocr_split_summary.json`

## Local Snapshot Estimates

These numbers came from the current local `data/manifest_full.jsonl` and are only an estimate based on the manifest available in this repo right now.

From `data/manifest_no_english_summary.json`:

- total manifest rows: `1204`
- rows kept after excluding English: `855`
- rows excluded for English: `349`
- known kept PDF size: about `5.35 GB`

Implication:

- A `100 GB` laptop is comfortably enough for this current dataset slice.

## What Was Verified In This Session

Verified:

- the new filter command exists and works
- the new OCR split command exists and works on local sample data
- the fresh-laptop orchestration script exists
- test suite passes

Test command used:

```powershell
python -m unittest discover -s tests -p "test*.py" -v
```

Status at end of session:

- `11/11` tests passed

## What Was Not Run

These were intentionally **not** run end-to-end in this session:

- the full fresh-laptop download script
- a full OCR split over the large fetched dataset
- the full extraction stage for all documents

Only a small local smoke test was run for the OCR split on sample data.

## README Coverage

The README was updated to document:

- `filter-manifest`
- `split-fetch-by-ocr`
- the no-English filtering flow

## Suggested Next Step For Codex On The New Laptop

1. Confirm Python environment and dependencies are installed.
2. Confirm OCR prerequisites if OCR extraction will be used later:
   - `pytesseract`
   - local `tesseract`
   - Nepali OCR language data if needed
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_full_no_english_download.ps1
```

4. After download completes, inspect:
   - `data/fetch_no_english_good.jsonl`
   - `data/fetch_no_english_needs_ocr.jsonl`
   - `data/fetch_no_english_ocr_split_summary.json`

5. Then create or run the extraction stage in two groups:
   - `good` PDFs with `--ocr-mode never`
   - `needs_ocr` PDFs with `--ocr-mode required` or `--ocr-mode auto`

## Notes For A Future Codex Session

- Do not assume the target is “literature-only”. The latest confirmed requirement was “remove every English content”.
- Do not assume downloads have already been done on the new laptop.
- Do not rerun old local-download artifacts from this laptop unless explicitly needed.
- If the user later wants “all non-English but no textbooks”, update the script to include `--exclude-textbooks`.

## Files Changed In This Session

- `README.md`
- `epustakalaya_corpus/cli.py`
- `epustakalaya_corpus/pipeline.py`
- `scripts/run_full_no_english_download.ps1`
- `tests/test_filter_manifest.py`
- `tests/test_filter_modes.py`
- `tests/test_pdf_classification.py`
