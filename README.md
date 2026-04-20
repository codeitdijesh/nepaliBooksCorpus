# E-Pustakalaya Corpus Pipeline

This workspace now contains a practical pipeline for building a `pustakalaya.org` text corpus without assuming that every document is safely redistributable as a raw PDF.

The pipeline is split into nine explicit stages:

1. `crawl-manifest`: enumerate search pages and collect per-document metadata.
2. `filter-manifest`: carve out a smaller manifest before any network-heavy probe or download.
3. `probe-access`: classify whether each document exposes a direct PDF URL.
4. `fetch-pdfs`: download only documents that probed as directly retrievable.
5. `split-fetch-by-ocr`: inspect downloaded PDFs and separate native-text PDFs from PDFs that will need OCR.
6. `extract-text`: run native PDF extraction first and OCR only when needed.
7. `package-corpus`: merge metadata, probe, fetch, and extraction outputs into a final JSONL corpus.
8. `summarize-manifest`: estimate storage needs from manifest file sizes.
9. `summarize-probe`: summarize which documents are directly downloadable.

## Layout

- `epustakalaya_corpus/`: CLI package and pipeline logic
- `tests/`: parser-focused unit tests

## Requirements

The current environment already includes `requests`, `lxml`, `PyMuPDF`, and `Pillow`.

Optional OCR support requires:

- `pytesseract`
- a local `tesseract` binary
- Nepali OCR language data if you want `nep+eng`

Install any missing Python packages with:

```powershell
pip install -r requirements.txt
```

## Quick Start

Sample 1-page crawl:

```powershell
python -m epustakalaya_corpus crawl-manifest `
  --page-start 1 `
  --page-end 1 `
  --output data/manifest_sample.jsonl
```

Probe the first 10 documents from that manifest:

```powershell
python -m epustakalaya_corpus probe-access `
  --manifest data/manifest_sample.jsonl `
  --output data/probe_sample.jsonl `
  --limit 10
```

Create a literature-focused manifest before probing or download:

```powershell
python -m epustakalaya_corpus filter-manifest `
  --manifest data/manifest_full.jsonl `
  --output data/manifest_literature.jsonl `
  --summary data/manifest_literature_summary.json `
  --exclude-english `
  --exclude-textbooks `
  --include-literature
```

Exclude all English content before probing or download:

```powershell
python -m epustakalaya_corpus filter-manifest `
  --manifest data/manifest_full.jsonl `
  --output data/manifest_no_english.jsonl `
  --summary data/manifest_no_english_summary.json `
  --exclude-english
```

Download directly accessible PDFs:

```powershell
python -m epustakalaya_corpus fetch-pdfs `
  --probe data/probe_sample.jsonl `
  --download-dir data/pdfs `
  --output data/fetch_sample.jsonl
```

Split downloaded PDFs into native-text versus OCR-needed inventories:

```powershell
python -m epustakalaya_corpus split-fetch-by-ocr `
  --fetch data/fetch_sample.jsonl `
  --manifest data/manifest_sample.jsonl `
  --good-output data/fetch_sample_good.jsonl `
  --ocr-output data/fetch_sample_needs_ocr.jsonl `
  --summary data/fetch_sample_ocr_split_summary.json
```

Extract text with OCR fallback:

```powershell
python -m epustakalaya_corpus extract-text `
  --fetch data/fetch_sample.jsonl `
  --text-dir data/text `
  --output data/extract_sample.jsonl `
  --ocr-mode auto
```

Build the final corpus:

```powershell
python -m epustakalaya_corpus package-corpus `
  --manifest data/manifest_sample.jsonl `
  --probe data/probe_sample.jsonl `
  --fetch data/fetch_sample.jsonl `
  --extract data/extract_sample.jsonl `
  --output data/corpus_sample.jsonl `
  --summary data/corpus_summary.json
```

Estimate total storage from a manifest:

```powershell
python -m epustakalaya_corpus summarize-manifest `
  --manifest data/manifest_sample.jsonl `
  --output data/manifest_sample_summary.json
```

Summarize probe results:

```powershell
python -m epustakalaya_corpus summarize-probe `
  --probe data/probe_sample.jsonl `
  --output data/probe_sample_summary.json
```

## Operational Notes

- Default crawl behavior is intentionally conservative: one request at a time with a delay between requests.
- `probe-access` is where you should confirm whether direct PDF fetching works at scale before downloading thousands of files.
- `fetch-pdfs` stores one PDF per document ID as `<doc_id>.pdf`.
- `split-fetch-by-ocr` is a structural check on the downloaded PDFs. It tells you which files have usable embedded text and which ones should be routed through OCR-heavy extraction.
- `extract-text` writes both a per-document `.txt` file and a structured extraction report.
- `package-corpus` deduplicates by exact document ID and then by normalized text hash.

## Rights And Provenance

This pipeline stores explicit provenance fields in the final corpus, including:

- source URL
- detail page URL
- extracted PDF URL when available
- site-level license notice captured from the page
- extraction method and OCR flags

You should still review whether the final public dataset can include full text for each document you collect. This code does not make that legal decision for you.
