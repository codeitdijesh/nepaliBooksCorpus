from __future__ import annotations

import argparse

from .pipeline import (
    classify_fetch_for_ocr,
    crawl_manifest,
    extract_text,
    filter_manifest,
    fetch_pdfs,
    package_corpus,
    probe_access,
    summarize_manifest,
    summarize_probe,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a text corpus from pustakalaya.org documents.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl-manifest", help="Enumerate search results and fetch detail metadata.")
    crawl.add_argument("--output", required=True)
    crawl.add_argument("--page-start", type=int, default=1)
    crawl.add_argument("--page-end", type=int, default=1)
    crawl.add_argument("--query", default="")
    crawl.add_argument("--form-filter", default="")
    crawl.add_argument("--search-in", default="all")
    crawl.add_argument("--delay-seconds", type=float, default=1.5)
    crawl.add_argument("--timeout-seconds", type=int, default=30)
    crawl.add_argument("--resume", action="store_true")
    crawl.set_defaults(func=crawl_manifest)

    filter_cmd = subparsers.add_parser("filter-manifest", help="Create a smaller manifest before probing or download.")
    filter_cmd.add_argument("--manifest", required=True)
    filter_cmd.add_argument("--output", required=True)
    filter_cmd.add_argument("--summary")
    filter_cmd.add_argument("--exclude-english", action="store_true")
    filter_cmd.add_argument("--exclude-textbooks", action="store_true")
    filter_cmd.add_argument("--exclude-english-textbooks-only", action="store_true")
    filter_cmd.add_argument("--include-literature", action="store_true")
    filter_cmd.add_argument("--include-pattern", action="append", default=[])
    filter_cmd.add_argument("--exclude-pattern", action="append", default=[])
    filter_cmd.set_defaults(func=filter_manifest)

    probe = subparsers.add_parser("probe-access", help="Check whether manifest documents expose direct PDF access.")
    probe.add_argument("--manifest", required=True)
    probe.add_argument("--output", required=True)
    probe.add_argument("--limit", type=int, default=0)
    probe.add_argument("--delay-seconds", type=float, default=1.5)
    probe.add_argument("--timeout-seconds", type=int, default=30)
    probe.add_argument("--resume", action="store_true")
    probe.set_defaults(func=probe_access)

    fetch = subparsers.add_parser("fetch-pdfs", help="Download PDFs that probe as directly accessible.")
    fetch.add_argument("--probe", required=True)
    fetch.add_argument("--download-dir", required=True)
    fetch.add_argument("--output", required=True)
    fetch.add_argument("--limit", type=int, default=0)
    fetch.add_argument("--delay-seconds", type=float, default=2.0)
    fetch.add_argument("--timeout-seconds", type=int, default=60)
    fetch.add_argument("--overwrite", action="store_true")
    fetch.add_argument("--resume", action="store_true")
    fetch.set_defaults(func=fetch_pdfs)

    split_ocr = subparsers.add_parser(
        "split-fetch-by-ocr",
        help="Inspect downloaded PDFs and split them into native-text versus OCR-needed inventories.",
    )
    split_ocr.add_argument("--fetch", required=True)
    split_ocr.add_argument("--good-output", required=True)
    split_ocr.add_argument("--ocr-output", required=True)
    split_ocr.add_argument("--manifest")
    split_ocr.add_argument("--summary")
    split_ocr.add_argument("--min-chars-per-page", type=int, default=50)
    split_ocr.set_defaults(func=classify_fetch_for_ocr)

    extract = subparsers.add_parser("extract-text", help="Extract text from downloaded PDFs with optional OCR fallback.")
    extract.add_argument("--fetch", required=True)
    extract.add_argument("--text-dir", required=True)
    extract.add_argument("--output", required=True)
    extract.add_argument("--limit", type=int, default=0)
    extract.add_argument("--ocr-mode", choices=["never", "auto", "required"], default="auto")
    extract.add_argument("--ocr-lang", default="nep+eng")
    extract.add_argument("--min-chars-per-page", type=int, default=50)
    extract.add_argument("--resume", action="store_true")
    extract.set_defaults(func=extract_text)

    package = subparsers.add_parser("package-corpus", help="Merge pipeline outputs into the final JSONL corpus.")
    package.add_argument("--manifest", required=True)
    package.add_argument("--probe", required=True)
    package.add_argument("--fetch", required=True)
    package.add_argument("--extract", required=True)
    package.add_argument("--output", required=True)
    package.add_argument("--summary", required=True)
    package.set_defaults(func=package_corpus)

    manifest_summary = subparsers.add_parser("summarize-manifest", help="Estimate storage from manifest file_size labels.")
    manifest_summary.add_argument("--manifest", required=True)
    manifest_summary.add_argument("--output")
    manifest_summary.add_argument("--top-n", type=int, default=10)
    manifest_summary.set_defaults(func=summarize_manifest)

    probe_summary = subparsers.add_parser("summarize-probe", help="Summarize access modes and known download sizes from probe output.")
    probe_summary.add_argument("--probe", required=True)
    probe_summary.add_argument("--output")
    probe_summary.set_defaults(func=summarize_probe)

    args = parser.parse_args()
    return args.func(args)
