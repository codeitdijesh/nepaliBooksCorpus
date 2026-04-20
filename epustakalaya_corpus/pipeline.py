from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from .client import PustakalayaClient
from .parsers import parse_detail_page, parse_search_page
from .utils import (
    append_jsonl,
    ensure_dir,
    existing_ids,
    format_bytes,
    index_by,
    iso_now,
    parse_size_to_bytes,
    read_jsonl,
    sha256_file,
    text_hash_for_dedupe,
)


def _print_utf8(text: str) -> None:
    try:
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
    except Exception:  # noqa: BLE001
        print(text.encode("unicode_escape").decode("ascii"))


def crawl_manifest(args: Any) -> int:
    output = Path(args.output)
    done = existing_ids(output) if args.resume else set()
    client = PustakalayaClient(delay_seconds=args.delay_seconds, timeout_seconds=args.timeout_seconds)
    processed_docs = 0

    total_pages = args.page_end
    current_page = args.page_start
    _print_utf8(
        f"crawl-manifest start page_start={args.page_start} page_end={args.page_end} resume={args.resume} output={output}"
    )
    while current_page <= total_pages:
        page_html = client.fetch_search_page(
            page=current_page,
            query=args.query,
            form_filter=args.form_filter,
            search_in=args.search_in,
        )
        parsed_page = parse_search_page(page_html, client.base_url)
        total_pages = min(parsed_page["total_pages"], args.page_end or parsed_page["total_pages"])

        for result in parsed_page["results"]:
            doc_id = result["doc_id"]
            if doc_id in done:
                continue
            detail_html = client.fetch_detail_page(result["detail_url"])
            detail = parse_detail_page(detail_html, result["detail_url"])
            row = {
                **result,
                **detail,
                "crawl_page": current_page,
                "crawl_timestamp": iso_now(),
                "source": "pustakalaya.org",
            }
            append_jsonl(output, row)
            done.add(doc_id)
            processed_docs += 1

        _print_utf8(
            f"crawl-manifest page_complete page={current_page} total_pages_seen={parsed_page['total_pages']} processed_docs={processed_docs}"
        )
        current_page += 1
    _print_utf8(f"crawl-manifest done processed_docs={processed_docs} output={output}")
    return 0


def probe_access(args: Any) -> int:
    manifest_rows = read_jsonl(Path(args.manifest))
    output = Path(args.output)
    done = existing_ids(output) if args.resume else set()
    client = PustakalayaClient(delay_seconds=args.delay_seconds, timeout_seconds=args.timeout_seconds)

    processed = 0
    _print_utf8(f"probe-access start manifest={args.manifest} limit={args.limit} resume={args.resume} output={output}")
    for row in manifest_rows:
        doc_id = str(row["doc_id"])
        if doc_id in done:
            continue
        if args.limit and processed >= args.limit:
            break

        pdf_url = row.get("pdf_url")
        access_mode = "missing_pdf_url"
        probe = {
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "final_url": None,
        }
        probe_error = None

        if pdf_url:
            try:
                probe = client.probe_pdf(pdf_url)
                content_type = (probe.get("content_type") or "").lower()
                if "pdf" in content_type:
                    access_mode = "direct_pdf"
                elif "html" in content_type:
                    access_mode = "viewer_only"
                else:
                    access_mode = "reachable_non_pdf"
            except Exception as exc:  # noqa: BLE001
                probe_error = str(exc)
                access_mode = "probe_failed"
        elif row.get("login_link_present"):
            access_mode = "session_gated"

        result = {
            "doc_id": doc_id,
            "detail_url": row.get("detail_url"),
            "pdf_url": pdf_url,
            "access_mode": access_mode,
            "login_link_present": bool(row.get("login_link_present")),
            "download_count_url": row.get("download_count_url"),
            "probe_timestamp": iso_now(),
            "probe_error": probe_error,
            **probe,
        }
        append_jsonl(output, result)
        done.add(doc_id)
        processed += 1
        if processed % 100 == 0:
            _print_utf8(f"probe-access progress processed={processed} output={output}")
    _print_utf8(f"probe-access done processed={processed} output={output}")
    return 0


def fetch_pdfs(args: Any) -> int:
    probe_rows = read_jsonl(Path(args.probe))
    output = Path(args.output)
    done = existing_ids(output) if args.resume else set()
    download_dir = Path(args.download_dir)
    ensure_dir(download_dir)
    client = PustakalayaClient(delay_seconds=args.delay_seconds, timeout_seconds=args.timeout_seconds)

    processed = 0
    _print_utf8(
        f"fetch-pdfs start probe={args.probe} download_dir={download_dir} limit={args.limit} resume={args.resume} output={output}"
    )
    for row in probe_rows:
        doc_id = str(row["doc_id"])
        if doc_id in done:
            continue
        if args.limit and processed >= args.limit:
            break

        pdf_url = row.get("pdf_url")
        if row.get("access_mode") != "direct_pdf" or not pdf_url:
            continue

        destination = download_dir / f"{doc_id}.pdf"
        fetch_error = None
        download = {}
        try:
            download = client.download_file(pdf_url, destination, overwrite=args.overwrite)
        except Exception as exc:  # noqa: BLE001
            fetch_error = str(exc)

        result = {
            "doc_id": doc_id,
            "detail_url": row.get("detail_url"),
            "pdf_url": pdf_url,
            "pdf_path": str(destination),
            "fetch_timestamp": iso_now(),
            "fetch_error": fetch_error,
            **download,
        }
        if destination.exists():
            result["sha256"] = sha256_file(destination)
        append_jsonl(output, result)
        done.add(doc_id)
        processed += 1
        if processed % 25 == 0:
            _print_utf8(f"fetch-pdfs progress processed={processed} output={output}")
    _print_utf8(f"fetch-pdfs done processed={processed} output={output}")
    return 0


def extract_text(args: Any) -> int:
    fetch_rows = read_jsonl(Path(args.fetch))
    output = Path(args.output)
    done = existing_ids(output) if args.resume else set()
    text_dir = Path(args.text_dir)
    ensure_dir(text_dir)

    ocr_enabled, pytesseract_module = _load_ocr_support()
    tesseract_path = shutil.which("tesseract")
    processed = 0
    _print_utf8(
        f"extract-text start fetch={args.fetch} text_dir={text_dir} limit={args.limit} resume={args.resume} ocr_mode={args.ocr_mode} output={output}"
    )

    for row in fetch_rows:
        doc_id = str(row["doc_id"])
        if doc_id in done:
            continue
        if args.limit and processed >= args.limit:
            break

        pdf_path = Path(row["pdf_path"])
        if not pdf_path.exists():
            continue

        text_path = text_dir / f"{doc_id}.txt"
        result = {
            "doc_id": doc_id,
            "pdf_path": str(pdf_path),
            "text_path": str(text_path),
            "extract_timestamp": iso_now(),
            "ocr_mode": args.ocr_mode,
            "ocr_available": bool(ocr_enabled and tesseract_path),
        }

        try:
            extracted = _extract_document_text(
                pdf_path=pdf_path,
                text_path=text_path,
                ocr_mode=args.ocr_mode,
                ocr_lang=args.ocr_lang,
                min_chars_per_page=args.min_chars_per_page,
                pytesseract_module=pytesseract_module if ocr_enabled and tesseract_path else None,
            )
            result.update(extracted)
        except Exception as exc:  # noqa: BLE001
            result["extract_error"] = str(exc)

        append_jsonl(output, result)
        done.add(doc_id)
        processed += 1
        if processed % 25 == 0:
            _print_utf8(f"extract-text progress processed={processed} output={output}")
    _print_utf8(f"extract-text done processed={processed} output={output}")
    return 0


def package_corpus(args: Any) -> int:
    manifest = index_by(read_jsonl(Path(args.manifest)), "doc_id")
    probe = index_by(read_jsonl(Path(args.probe)), "doc_id")
    fetch = index_by(read_jsonl(Path(args.fetch)), "doc_id")
    extract = index_by(read_jsonl(Path(args.extract)), "doc_id")

    output = Path(args.output)
    summary_path = Path(args.summary)
    seen_doc_ids: set[str] = set()
    seen_text_hashes: set[str] = set()

    summary = {
        "packaged_at": iso_now(),
        "manifest_rows": len(manifest),
        "probe_rows": len(probe),
        "fetch_rows": len(fetch),
        "extract_rows": len(extract),
        "included_rows": 0,
        "skipped_duplicate_doc_id": 0,
        "skipped_duplicate_text": 0,
        "skipped_missing_text": 0,
    }

    if output.exists():
        output.unlink()

    _print_utf8(
        f"package-corpus start manifest={args.manifest} probe={args.probe} fetch={args.fetch} extract={args.extract} output={output}"
    )
    for doc_id, manifest_row in manifest.items():
        extract_row = extract.get(doc_id)
        if not extract_row:
            summary["skipped_missing_text"] += 1
            continue
        text_path_value = extract_row.get("text_path")
        if not text_path_value:
            summary["skipped_missing_text"] += 1
            continue
        text_path = Path(text_path_value)
        if not text_path.exists():
            summary["skipped_missing_text"] += 1
            continue

        text = text_path.read_text(encoding="utf-8")
        if not text.strip():
            summary["skipped_missing_text"] += 1
            continue

        if doc_id in seen_doc_ids:
            summary["skipped_duplicate_doc_id"] += 1
            continue

        text_hash = text_hash_for_dedupe(text)
        if text_hash in seen_text_hashes:
            summary["skipped_duplicate_text"] += 1
            continue

        row = {
            "doc_id": doc_id,
            "title": manifest_row.get("title"),
            "source": manifest_row.get("source"),
            "source_url": manifest_row.get("pdf_url") or (probe.get(doc_id) or {}).get("pdf_url"),
            "detail_url": manifest_row.get("detail_url"),
            "language": manifest_row.get("language"),
            "publisher": manifest_row.get("publisher"),
            "publication_year": manifest_row.get("publication_year"),
            "pages_total": manifest_row.get("pages_total"),
            "keywords": manifest_row.get("keywords"),
            "site_license_notice": manifest_row.get("site_license_notice"),
            "access_mode": (probe.get(doc_id) or {}).get("access_mode"),
            "pdf_path": (fetch.get(doc_id) or {}).get("pdf_path"),
            "text_path": str(text_path),
            "text_hash": text_hash,
            "extraction_method": extract_row.get("extraction_method"),
            "ocr_used": extract_row.get("ocr_used"),
            "pages_ocr": extract_row.get("pages_ocr"),
            "native_pages": extract_row.get("native_pages"),
            "chars_total": extract_row.get("chars_total"),
            "text": text,
            "metadata": manifest_row.get("metadata"),
        }
        append_jsonl(output, row)
        seen_doc_ids.add(doc_id)
        seen_text_hashes.add(text_hash)
        summary["included_rows"] += 1

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_utf8(f"package-corpus done included_rows={summary['included_rows']} output={output}")
    return 0


def summarize_manifest(args: Any) -> int:
    manifest_rows = read_jsonl(Path(args.manifest))
    output = Path(args.output) if args.output else None

    total_rows = len(manifest_rows)
    rows_with_size = 0
    total_bytes = 0
    largest: list[dict[str, Any]] = []

    for row in manifest_rows:
        size_bytes = parse_size_to_bytes(row.get("file_size_label"))
        if size_bytes is None:
            continue
        rows_with_size += 1
        total_bytes += size_bytes
        largest.append(
            {
                "doc_id": row.get("doc_id"),
                "title": row.get("title"),
                "file_size_label": row.get("file_size_label"),
                "size_bytes": size_bytes,
                "detail_url": row.get("detail_url"),
            }
        )

    largest.sort(key=lambda item: item["size_bytes"], reverse=True)
    summary = {
        "manifest_path": str(Path(args.manifest)),
        "rows_total": total_rows,
        "rows_with_size": rows_with_size,
        "rows_missing_size": total_rows - rows_with_size,
        "total_bytes_known": total_bytes,
        "total_size_known": format_bytes(total_bytes),
        "average_size_known_bytes": int(total_bytes / rows_with_size) if rows_with_size else 0,
        "average_size_known": format_bytes(int(total_bytes / rows_with_size)) if rows_with_size else "0 B",
        "largest_files": largest[: args.top_n],
    }

    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    _print_utf8(rendered)
    return 0


def summarize_probe(args: Any) -> int:
    probe_rows = read_jsonl(Path(args.probe))
    output = Path(args.output) if args.output else None

    counts: dict[str, int] = {}
    direct_bytes = 0
    direct_count = 0
    for row in probe_rows:
        access_mode = str(row.get("access_mode") or "unknown")
        counts[access_mode] = counts.get(access_mode, 0) + 1
        if access_mode == "direct_pdf" and row.get("content_length"):
            direct_count += 1
            direct_bytes += int(row["content_length"])

    summary = {
        "probe_path": str(Path(args.probe)),
        "rows_total": len(probe_rows),
        "access_mode_counts": counts,
        "direct_pdf_rows_with_content_length": direct_count,
        "direct_pdf_bytes_known": direct_bytes,
        "direct_pdf_size_known": format_bytes(direct_bytes),
    }

    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    _print_utf8(rendered)
    return 0


def _extract_document_text(
    pdf_path: Path,
    text_path: Path,
    ocr_mode: str,
    ocr_lang: str,
    min_chars_per_page: int,
    pytesseract_module: Any | None,
) -> dict[str, Any]:
    pages_out: list[str] = []
    pages_ocr = 0
    native_pages = 0

    with fitz.open(pdf_path) as document:
        for page in document:
            native_text = page.get_text("text", sort=True).strip()
            use_ocr = False

            if ocr_mode == "required":
                use_ocr = True
            elif ocr_mode == "auto":
                use_ocr = len(native_text) < min_chars_per_page

            page_text = native_text
            if use_ocr and pytesseract_module is not None:
                page_text = _ocr_page(page, pytesseract_module, ocr_lang).strip()
                if page_text:
                    pages_ocr += 1
                elif native_text:
                    native_pages += 1
                    page_text = native_text
            elif native_text:
                native_pages += 1

            pages_out.append(page_text)

    full_text = "\n\n".join(text for text in pages_out if text).strip()
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(full_text, encoding="utf-8")

    if pages_ocr and native_pages:
        extraction_method = "mixed"
    elif pages_ocr:
        extraction_method = "ocr"
    else:
        extraction_method = "native"

    return {
        "pages_total": len(pages_out),
        "pages_ocr": pages_ocr,
        "native_pages": native_pages,
        "chars_total": len(full_text),
        "ocr_used": pages_ocr > 0,
        "extraction_method": extraction_method,
    }


def _ocr_page(page: fitz.Page, pytesseract_module: Any, ocr_lang: str) -> str:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    try:
        return pytesseract_module.image_to_string(image, lang=ocr_lang)
    except Exception:  # noqa: BLE001
        return ""


def _load_ocr_support() -> tuple[bool, Any | None]:
    try:
        import pytesseract  # type: ignore

        return True, pytesseract
    except Exception:  # noqa: BLE001
        return False, None
